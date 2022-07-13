#module libraries for multi-client networking
from socket import *
from pickle import *
from _thread import *

#module library for database management
import mysql.connector as db

#other module libraries
from time import *
from random import *
from string import *

def print_update(update):
    #get the current time and print it with the update
    now = strftime("%H:%M:%S", localtime())
    print("[" + now + "]", update)

def start_server():
    #set up global lists
    global priv_games, pub_games, active_players
    priv_games = []
    pub_games = []
    active_players = []

    #set up the server and wait for connections
    server = socket(AF_INET, SOCK_STREAM) 
    server.bind(("127.0.0.1", 12345))
    server.listen()
    print_update("Server started")

    #continuously accept connections and start a new thread for each one 
    while True:
        conn, address = server.accept() 
        ip_address = str(address[0])
        port = str(address[1])
        print_update("Connected to: " + ip_address + " on port: " + port)
        start_new_thread(service_client, (conn, ip_address))

def service_client(conn, addr):
    #set up client status variables
    connected = True
    logged_in = False
    in_game = False

    #recieve commands from clients while they're connected to the server
    while connected:
        try:
            #receive data and extract the client's command from it 
            data = conn.recv(4096)
            instruction = loads(data)
            command = instruction["command"]

            #process the client's command
            if command == "register":
                #try to create a new account for the client
                username = instruction["user"]
                password = instruction["pswd"]
                reply = register_user(username, password)
                conn.sendall(reply.encode())

                #print server update
                if reply == "Success":
                    print_update("Account created for " + addr + "\n Username: " +
                                 username)

                    #make the client a player object and set logged in status variable
                    player = Player(username)
                    logged_in = True

                else:
                    print_update("Registration failed for " + addr)

            elif command == "login":
                #try to log the client in
                username = instruction["user"]
                password = instruction["pswd"]
                reply = login(username, password)
                conn.sendall(reply.encode())

                #print server update
                if reply == "Success":
                    print_update(addr + " logged in as " + username)

                    #make the client a player and set the logged in status variable 
                    player = Player(username)
                    logged_in = True

                else:
                    print_update("Login failed for " + addr)

            elif command == "check stats":
                #send the user their game statistics from the database
                reply = get_stats(username)
                conn.sendall(dumps(reply))

                #print server update
                print_update("Fetching game statistics for " + username)

            elif command == "read rules":
                #open and read the rules file then send the contents to the user
                reply = read_rules()
                conn.sendall(reply.encode())

                #print server update
                print_update("Fetching game rules for " + username)

            elif command == "log out":
                #remove the player from the active player list
                active_players.remove(username)
                conn.sendall(b"Success")

                #print server update and set the logged in status variable
                print_update(username + " has logged out")
                logged_in = False

            elif command == "create game":
                #create a game room of the specified type (private or public)
                game_type = instruction["type"]
                game = Game(game_type)

                #print server update
                print_update("Creating a " + game_type + " game for " + username +
                             "\n Game code: " + game.code)               

                #make the client the host player of the game 
                #and set the in game status variable
                player.host = True
                game.add_player(player)
                in_game = True

                #send the room code to the client
                reply = game.code    
                conn.sendall(reply.encode())

            elif command == "join priv":
                #try to let the client into their chosen game room
                room_code = instruction["code"]
                outcome = enter_priv_room(room_code, player)
                reply = outcome[0]
                conn.sendall(reply.encode())

                #print server status
                if reply == "Success":
                    print_update(username + " joined room: " + room_code)

                    #keep a reference to the game the client joined 
                    #and set the in game status variable
                    game = outcome[1]
                    in_game = True

                elif outcome == "Invalid room code":
                    print_update(username + " entered an invalid room code")

                elif outcome == "Room is full":
                    print_update(username + " tried to enter a full game room")

                elif outcome == "Game has started":
                    print_update(username + " tried to enter a game that" 
                                 "has already started")

            elif command == "get pub games":
                #send the client a list of the current public game room codes 
                #and capacities               
                reply = get_pub_games()
                conn.sendall(dumps(reply))

                #print server update
                print_update("Sending " + username + " the public games list")

            elif command == "join pub":
                #try to let the client into their chosen game room
                room_code = instruction["code"]
                outcome = enter_pub_room(room_code, player)
                reply = outcome[0]
                conn.sendall(reply.encode())

                #print server update
                if reply == "Success":                   
                    print_update(username + " joined room: " + room_code)

                    #keep a reference to the game the client joined 
                    #and set the in game status variable
                    game = outcome[1]
                    in_game = True

                elif outcome == "Room is full":
                    print_update(username + " tried to enter a full game room")

                elif outcome == "Game has started":
                    print_update(username + " tried to enter a game that has"  
                                 "already started")

                elif outcome == "Game room is no longer valid":
                    print_update(username + " tried to enter a game that no longer" 
                                 "exists")

            elif command == "update lobby":
                #send the client a list of their game room's current players
                reply = [game.get_player_names()]

                #send the host a signal if there are enough players to start
                if game.enough_players() and player.host:
                   reply.append("can start")

                #send the client a signal to change their display 
                #if the game has started
                elif game.status == "started":
                   reply.append("started")

                #send the client a signal to stop asking for updates 
                #if the lobby has closed
                elif game.status == "ended":
                    reply.append("ended")

                else:
                    #send the client a signal to keep waiting for the room to fill
                    reply.append("waiting")
                conn.sendall(dumps(reply))

                #print server update
                print_update("Sending game lobby updates for " + game.code + " to " +
                            username)

            elif command == "leave room":
                #remove the player from their game and set the in game status variable
                game.remove_player(player)
                in_game = False
                conn.sendall(b"Success")

                #print server update
                print_update(username + " has left game " + game.code)
                if game.status == "ended":
                    print_update("Game " + game.code + " has ended") 
                     
            elif command == "start game":
                #start the game if there are enough players 
                #and tell the client whether the game could be started
                if game.enough_players():
                    game.set_up()
                    reply = "Success"

                    #print server update
                    print_update("Game " + game.code + " started")

                else:
                    reply = "Failure"

                    #print server update
                    print_update("Failed to start " + game.code)
                conn.sendall(reply.encode())       

            elif command == "set up game display":
                #send the client details about their game 
                reply = {"players": game.get_player_names(), 
                         "hand": player.get_card_names()}
                conn.sendall(dumps(reply))
               
                #set up update variable
                update = ""

                #print server update
                print_update("Sending " + username + " details about game " + 
                             game.code)

            elif command == "check cards":
                #check if the client's card choice is valid               
                cards = instruction["cards"]
                reply = check_cards(cards, player)
                conn.sendall(reply.encode())

                #print server update
                print_update(username + " is trying to have their turn")
                if reply in ("Choose player", "Success"):
                    #update the card played variable 
                    #and remove the cards from the player's hand
                    game.card_played = cards[0]
                    player.remove_cards(cards)

                    if reply == "Choose player":
                        print_update(username + "'s being prompted to choose a player"  
                                     " to act against")

                    else: 
                        #set the nope player variable to the player whose turn is next
                        game.nope_player = game.get_next_player().name 

                else:
                    print_update(username + "'s card choice was invalid")

            elif command == "choose player":
                #store the name of the player the client has chosen to act against
                #as the nope player and the chosen player, 
                #and change the game's latest update
                game.nope_player = instruction["player"]
                game.chosen_player = game.nope_player
                game.latest_update = game.get_current_player().name + " wants to \n" \
                                    "take cards from " + game.nope_player
                conn.sendall(b"Success")

                #print server update
                print_update(username + " has chosen to take a card from " +
                             game.nope_player)       

            elif command == "choose card":
                #store the name of the card the client has chosen to give away
                game.given_card = instruction["card"]
                conn.sendall(b"Success")

            elif command == "draw card":
                #end the client's turn by drawing a card               
                reply = player.end_turn(game)
                conn.sendall(reply.encode())

                #print server update
                print_update(username + " is drawing a card")
                if reply == "No Defuse":
                    print_update(username + " is dead")
                
            elif command == "update game":
                #send the client updates about the game
                reply = {"turn":game.get_current_player().name, "turn over":False,
                         "card played":game.card_played, "can nope": False, 
                         "new update":False, "status": game.status, 
                         "hand": player.get_card_names(), "see the future":False,
                         "choose card":False}
                
                if game.status != "ended":    
                    #check if any parts of the reply need to be changed
                    #or if any updates to the game need to be made
                    if game.nope_player == username:
                        if player.has_card("Nope"):
                            #if the nope player has a nope card send a signal to let
                            #them know they can use it
                            reply["can nope"] = True

                        else:
                            #if the nope player doesn't have a nope card, the current 
                            #turn can't be noped
                            game.turn_noped = "False"
                        #reset nope player variable so the message's only sent once
                        game.nope_player = ""

                    if game.turn_noped == "False" and game.card_played == "Favour" \
                        and game.chosen_player == username:
                        #prompt the client to choose a card to give if a favour card's 
                        #played against them and they haven't already chosen one
                        if not player.card_chosen:
                            reply["choose card"] = True
                            player.card_chosen = True

                    elif game.get_current_player().name == username:
                        if game.turn_noped == "True":
                            #send a signal to let the player know their turn's over
                            reply["turn over"] = True

                            #reset turn noped variable so the message's only sent once
                            game.turn_noped = ""

                        elif game.turn_noped == "False":
                            #change the game's latest update
                            game.latest_update = "It's " + \
                                                game.get_current_player().name + "'s turn" 
                            
                            #play cards (a favour card can't be played until the other 
                            #player has chosen a card to give)
                            if cards[0] != "Favour" or game.given_card:
                                #get the card object that corresponds with the name of the 
                                #card being played
                                card = Deck.card_dict[cards[0]]

                                #send the cards at the top of the deck if a 
                                #see the future card is played
                                future_cards = card.play(game)
                                if future_cards:
                                    reply["see the future"] = future_cards

                                #send a signal to let the client know their turn's over
                                reply["turn over"] = True

                                #reset the card chosen, chosen player and 
                                #given card variables
                                for user in game.players:
                                    user.card_chosen = False
                                    game.chosen_player = False
                                    game.given_card = False

                                #reset turn noped variable so the message's only sent once
                                game.turn_noped = ""
                                
                    if update != game.latest_update:
                        #send the client the latest game update if it's different to the 
                        #last one sent
                        reply["new update"] = game.latest_update
                        update = game.latest_update

                else:
                    #set the in game status variable and update the player's 
                    #game statistics 
                    in_game = False                   
                    update_stats(player)

                #print server update
                print_update("Sending updates about game " + game.code + " to " +
                             username)
                conn.sendall(dumps(reply)) 

            elif command == "check nope":
                #check if the nope player chose to play their nope card
                if instruction["noped"]:    
                    #if they played their nope card, change the game's latest update,
                    #remove a nope card from their hand, and update other variables
                    game.latest_update = username + " played a Nope card. \n It's " \
                                         + game.get_current_player().name + "'s turn"
                    player.remove_cards(["Nope"])
                    game.turn_noped = "True"                     
                    game.card_played = "Nope"

                    #print server update
                    print_update(username + " played a Nope card")

                else:
                    #set the turn noped variable
                    game.turn_noped = "False"
                conn.sendall(b"Success")

            elif command == "count deck":
                #send the client the number of cards remaining in the deck               
                reply = str(len(game.deck.cards))
                conn.sendall(reply.encode())

                #print server update
                print_update("Sending " + username + " the number of cards left in" 
                             "the deck")

            elif command == "place kitten":
                #put an exploding kitten card in the position chosen by the client
                position = int(instruction["position"])
                game.deck.enqueue(ExplodingKittenCard(), position)

                #move to the next player's turn unless the player was attacked
                if player.attacked:
                    #reset the attacked variable so 
                    #the player only has to take two turns
                    player.attacked = False

                else:
                    game.next_players_turn()
                conn.sendall(b"Success")

            elif command == "accept death":
                #remove the player from the alive player list
                game.alive_players.remove(player)

                #check if the game is over
                if len(game.alive_players) > 1:
                    #move to the next player's turn if the game isn't over and change
                    #the game's latest update
                    game.whose_turn -= 1
                    game.latest_update = "It's " + game.get_current_player().name + \
                                         "'s turn"

                else:
                    #end the game if there's only one alive player remaining: update
                    #the game status and latest update, then determine the winner  
                    game.status = "ended"                   
                    game.latest_update = "The game is over, \n" + \
                                         game.alive_players[0].name + " won!"
                    game.alive_players[0].won = True

                    #print server update 
                    print_update(game.code + " has ended- " + 
                                 game.alive_players[0].name + " won")
                conn.sendall(b"Success")

            elif command == "close":
                #close the connection and set the connected status variable
                conn.close()
                connected = False
         
        except error:
            #close the connection and set the connected status variable
            #if there's an error
            print(error)
            conn.close()
            connected = False 

    if in_game: 
        #remove the player from their game if they're in one
        game.remove_player(player)

        #print server update
        print_update(username + " has left game " + game.code)
        if game.status == "ended":
            print_update("Game " + game.code + " has ended")  

    if logged_in:
        #log the client out if they're logged in 
        #by removing them from the active player list
        active_players.remove(username)

        #print server update
        print_update(username + " has logged out and exited the program")

    else:
        #print server update (ip address used as the player isn't logged in)
        print_update(addr + "has exited the program")

def db_connect():
    #connect to the User database
    db_User = db.connect(host="localhost", user="isobel", password="exploding", 
                         database="User")
    return db_User

def register_user(user, pwd):
    #connect to the User database
    db_User = db_connect()
    cursor = db_User.cursor()

    #check if the client's username has already been taken
    #escape query values to prevent SQL injection
    sql = "SELECT Username FROM User WHERE Username = %s"
    username = (user,)
    cursor.execute(sql, username)
    user_result = cursor.fetchall()

    #check if the client's password has already been taken
    #escape query values to prevent SQL injection
    sql = "SELECT Password FROM User WHERE Password = %s"
    password = (pwd,)
    cursor.execute(sql, password)
    pswd_result = cursor.fetchall()

    #return an error message if the username or password are taken
    if user_result and pswd_result:
        return "Username and password taken"
    elif user_result:
        return "Username taken"
    elif pswd_result:
        return "Password taken"

    #otherwise, register the client
    #escape query values to prevent SQL injection
    sql = "INSERT INTO User (Username, Password, NoGames, " \
        "NoWin, WinStreak, NoLoss, KittensDrawn, DefusesPlayed) " \
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    details = (user, pwd, 0, 0, 0, 0, 0, 0)
    cursor.execute(sql, details)
    db_User.commit()
    return "Success"

def login(user, pwd):
    #connect to the User database 
    db_User = db_connect()
    cursor = db_User.cursor()

    #check if the username and password are valid
    #escape query values to prevent SQL injection
    sql = "SELECT Username FROM User WHERE Username = %s AND Password = %s" 
    details = (user, pwd)
    cursor.execute(sql, details)
    result = cursor.fetchall()
    if result:
        if user not in active_players:
            return "Success"
        else:
            return "This account is logged in already"
    else:
        return "Username or password was incorrect"

def get_stats(user):
    #connect to the User database
    db_User = db_connect()
    cursor = db_User.cursor()

    #fetch and return statistics from the database 
    sql = "SELECT NoGames, NoWin, WinStreak, NoLoss, KittensDrawn, DefusesPlayed "\
          "FROM User WHERE Username = '" + user + "'"
    cursor.execute(sql)
    return cursor.fetchone()

def read_rules():
    #open and read the rules file
    with open("GameRules.txt", "r") as rules_file:
        return rules_file.read()

def enter_priv_room(code, player):
    #check if the game code is valid and the room isn't full
    for game in priv_games:
        if game.code == code:
            if game.status == "is not full":
                return [game.add_player(player), game]
    return ["Invalid room code"]

def get_pub_games():
    #generate a list of the available public games and their capacities
    game_list = []
    for game in pub_games:
        if game.status == "is not full":
            player_number = len(game.players)
            game_list.append([game.code, player_number])
    return game_list

def enter_pub_room(code, player):
    #try to enter the room if it isn't full and the game hasn't started
    for game in pub_games:
        if game.code == code:
            return game.add_player(player), game
    #if the game isn't in the list, it no longer exists
    return ["Game room is no longer valid"]

def check_cards(cards, player):
    #check if the player has chosen too many or few cards
    if len(cards) > 2:
        return "Only up to two cards \n can be played at once"

    elif len(cards) == 0:
        return "At least one card \n must be played"

    #check if the player's choice of cards is valid
    cardtype = Deck.card_dict[cards[0]]
    if len(cards) == 2:
        if cards[0] != cards[1] or cardtype != Card:
            return "Only a pair of the \n same Cat Cards can be \n played together"

        else:
            return "Choose player"

    elif cardtype in (Card, NopeCard, DefuseCard):
        return "Invalid card choice"

    elif cardtype == FavourCard:
        return "Choose player"

    else:
        return "Success"

def update_stats(player):
    #get the stats currently stored in the database and convert the tuple into a list
    stats = list(get_stats(player.name))
    
    #update the statistic values
    stats[0] += 1 #number of games played
    stats[4] += player.kittens_drawn #number of exploding kittens drawn
    stats[5] += player.defuses_played #number of defuses played

    if player.won: 
        stats[1] += 1 #number of wins 
        stats[2] += 1 #increment win streak

    else:
        stats[3] += 1 #number of losses
        stats[2] = 0 #win streak

    #reset the variables for updating the stats
    player.won = False
    player.kittens_drawn = 0
    player.defuses_played = 0 

    #connect to User database
    db_User = db_connect()
    cursor = db_User.cursor()

    #update the user's game statistics
    #escape query values to prevent SQL injection
    sql = "Update User SET NoGames = %s, NoWin = %s, WinStreak = %s, NoLoss = %s," \
        "KittensDrawn = %s, DefusesPlayed = %s WHERE Username = '" + player.name + "'" 
    new_stats = tuple(stats)
    cursor.execute(sql, new_stats)
    db_User.commit()

class Game:

    def __init__(self, game_type):
        #create a game room
        self.type = game_type
        self.code = self.generate_code()
        self.status = "is not full"
        self.players = []

    def generate_code(self):
        #generate random room code
        code = ''.join(choice(ascii_uppercase) for i in range(6))

        #check that the code isn't alredy in use
        if code in priv_games or code in pub_games:
            #make a new code if the code's already in use
            self.generate_code()

        else:
            #add the game code to the appropriate games list 
            if self.type == "public":
                pub_games.append(self)

            elif self.type == "private":
                priv_games.append(self)
        return code

    def update_status(self):
        #update (if the game hasn't started) the game status
        if self.status != "started":
            #a game can be played with up to 5 players
            if len(self.players) == 5:
                self.status = "is full"
            else:
                self.status = "is not full"

    def add_player(self, player):
        #add player to the game if possible 
        if self.status == "is not full":
            #add the player to the game and update the game's status
            self.players.append(player)
            self.update_status()
            return "Success"

        elif self.status == "is full":
            return "Room is full"

        elif self.status == "started":
            return "Game has started"

    def get_player_names(self):
        #generate a list of the names of the game's players
        return [player.name for player in self.players]

    def enough_players(self):
        #check if the game has enough players (more than 1) to start
        if len(self.players) > 1:
            return True
        else:
            return False

    def remove_player(self, player):
        #reset the player host variable so they won't automatically be the host of
        #the next game they join
        player.host = False

        #end the game if it has already started or they were the game's only player
        if self.status == "started" or len(self.players) == 1:
            self.status = "ended"

            #remove the game from the appropriate list
            if self.type == "public":
                pub_games.remove(self)

            else:
                priv_games.remove(self)
            
            #change the game's latest update
            self.latest_update = player.name + " has left the game"

        else:
            #remove the player from the game, make a new player the host 
            #and update the game status
            self.players.remove(player)
            self.players[0].host = True
            self.update_status()

    def set_up(self):
        #change the game's status and set up other status variables
        self.status = "started"
        self.whose_turn = 0
        self.nope_player = ""
        self.chosen_player = False
        self.turn_noped = ""
        self.latest_update = ""
        self.card_played = ""
        self.given_card = False

        for player in self.players:
            #set up status variables for the game's players
            player.attacked = False
            player.card_chosen = False

            #set up variables for updating the players' game statistics
            player.won = False
            player.kittens_drawn = 0
            player.defuses_played = 0

        #shuffle the player list to determine the order 
        #and change the game's latest update
        self.alive_players = self.players
        shuffle(self.alive_players)
        self.latest_update = "It's " + self.get_current_player().name + "'s turn"

        #set up a deck 
        self.deck = Deck(self)

        #deal a hand to each player 
        for player in self.alive_players:
            #each player gets 7 random cards and a defuse card
            player.hand = [self.deck.dequeue() for i in range(7)]
            player.hand.append(DefuseCard())

        #put the exploding kittens in the deck
        self.deck.add_kittens(self)

    def get_next_player(self):
        #the next player is next in the alive player list unless the current player
        #is the last player in the list, in which case the next player is the first
        #player in the list
        index = self.whose_turn + 1
        try:
           return self.alive_players[index]
        except:
           return self.alive_players[0]

    def get_current_player(self):       
        #get the player in the index of the whose turn variable
        return self.alive_players[self.whose_turn] 

    def next_players_turn(self):
        #move to the next player's turn and change the game's latest update
        self.whose_turn = self.alive_players.index(self.get_next_player())
        self.latest_update = "It's " + self.get_current_player().name + "'s turn"

class Player:

    def __init__(self, name):
        #create a player and add them to the active player list
        self.name = name 
        self.hand = []
        self.host = False
        active_players.append(name)

    def get_card_names(self):
        #get the names of the cards in the player's hand
        return [card.name for card in self.hand]

    def has_card(self, search_card):
        #check if the player has a certain card
        for card in self.hand:
            if card.name == search_card:
                return True
        return False

    def remove_cards(self, cards):
        #remove the played card(s) from the player's hand
        for card_name in cards:
            for card in self.hand:
                if card.name == card_name:
                    self.hand.remove(card)
                    break

    def end_turn(self, game):
        #draw a card to end the player's turn
        card = game.deck.dequeue()
        if card.name == "Exploding Kitten":
            #update the kittens drawn variable if the player draws one
            self.kittens_drawn += 1
            if self.has_card("Defuse"):
                #play the player's defuse card if they have one: update the defuses
                #played variable, remove a defuse card from the player's deck, and
                #change the latest update variable
                self.defuses_played += 1
                self.remove_cards(["Defuse"])
                game.latest_update = self.name + " drew an \n Exploding Kitten but" \
                                    "\n they played a Defuse"               
                return "Defuse"

            else:
                #if the player doesn't have a defuse card they are dead so change the 
                #game's latest update
                game.latest_update = self.name + " drew an \n Exploding Kitten." \
                    "\n They are dead."
                return "No Defuse"

        else:
            #if any other card is drawn it's added to the player's hand and it's the 
            #next player's turn unless the player was attacked, in which case they
            #must take a second turn
            if self.attacked:
                #reset the attacked variable so they only have to take 2 turns
                self.attacked = False

            else:
                game.next_players_turn()
            self.hand.append(card)
            return "Success"
            
class Card:

    def __init__(self, name):
        #create a card
        self.name = name

    def play(game):
        #find the player the card's being played against
        for player in game.alive_players:
            if game.chosen_player == player.name:
                other_player = player
                break
        
        #choose a random card from the other player's hand 
        #and transfer it to the first player
        card = choice(other_player.hand)
        game.get_current_player().hand.append(card)
        other_player.hand.remove(card)

class ExplodingKittenCard(Card):
    
    def __init__(self):
        #create an exploding kitten card
        super().__init__("Exploding Kitten")

    def play(game):
        #this card can't be played
        pass

class FavourCard(Card):
    
    def __init__(self):
        #create a favour card
        super().__init__("Favour") 

    def play(game):
        #find the player the card's being played against
        for player in game.alive_players:
            if game.chosen_player == player.name:
                other_player = player
                break
        
        #take the chosen card from the other player's hand 
        #and transfer it to the first player
        for card in other_player.hand:
            if card.name == game.given_card:
                game.get_current_player().hand.append(card)
                other_player.hand.remove(card)
                break

class ShuffleCard(Card):
    
    def __init__(self):
        #create a shuffle card
        super().__init__("Shuffle")

    def play(game):
        #shuffle the deck 
        shuffle(game.deck.cards)

class SeeTheFutureCard(Card):
    
    def __init__(self):
        #create a see the future card
        super().__init__("See the Future")

    def play(game):
        #return the 3 cards at the top of the deck
        return [card.name for card in game.deck.cards[:3]]

class AttackCard(Card):
    
    def __init__(self):
        #create an attack card
        super().__init__("Attack")

    def play(game):
        #reset the current player's attacked variable, change to the next player's 
        #turn, and set their attacked variable
        game.get_current_player().attacked = False
        game.next_players_turn()
        game.get_current_player().attacked = True

class NopeCard(Card):
    
    def __init__(self):
        #create a nope card
        super().__init__("Nope")

    def play(game):
        #this card can't be played on the player's turn
        pass

class SkipCard(Card):
    
    def __init__(self):
        #create a skip card
        super().__init__("Skip") 

    def play(game):
        #if the player has been attacked then make them take another turn
        if game.get_current_player().attacked:
            #reset the player attacked variable so they only have to have two turns
            game.get_current_player().attacked = False
        else:
            #move to the next player's turn
            game.next_players_turn()

class DefuseCard(Card):
    
    def __init__(self):
        #create a defuse card
        super().__init__("Defuse")

    def play(game):
        #this card can't be played unless an exploding kitten is drawn
        pass

class Deck:
    #set up a dictionary which maps card names to card classes
    card_dict = {"Tacocat":Card, "Cattermelon":Card, "Hairy Potato Cat":Card,
                 "Beard Cat":Card, "Rainbow-Ralphing Cat":Card, "Attack":AttackCard, 
                 "Nope":NopeCard, "Defuse":DefuseCard, "Favour":FavourCard,
                 "See the Future":SeeTheFutureCard, "Shuffle":ShuffleCard, 
                 "Skip":SkipCard, "Exploding Kitten": ExplodingKittenCard}

    def __init__(self, game):
       #set up deck of cards as a queue
       self.cards = []
       
       #populate the deck with cards 
       for i in range(4):
           for cat_card in ("Tacocat", "Cattermelon", "Hairy Potato Cat", 
                            "Beard Cat", "Rainbow-Ralphing Cat"):
               self.enqueue(Card(cat_card))
           for card in (AttackCard, FavourCard, ShuffleCard, SkipCard):
               self.enqueue(card())
       for i in range(5):
           self.enqueue(NopeCard())
       for i in range(6):
           self.enqueue(SeeTheFutureCard())
       
       #add the defuse cards
       if len(game.players) > 3:
           defuse_number = 6 - len(game.players)

       else:
           defuse_number = 2
       for i in range(defuse_number):
           self.enqueue(DefuseCard())

       #shuffle the deck
       shuffle(self.cards)

    def add_kittens(self, game):
       #put the exploding kittens in the deck then reshuffle it
       for i in range(len(game.players) - 1):
           self.enqueue(ExplodingKittenCard())
       shuffle(self.cards)

    def enqueue(self, card, position = -1):
        #add a card to the queue; the default position to add to is the back
        if position == -1:
            self.cards.append(card)
        else:
            self.cards.insert(position - 1, card)

    def dequeue(self):
        #remove a card from the front of the queue
        return self.cards.pop(0)

start_server()