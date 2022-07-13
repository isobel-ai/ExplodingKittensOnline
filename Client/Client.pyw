#module libraries for the GUI
from tkinter import *
from tkinter import scrolledtext
from tkinter import messagebox
from tkinter import font

#module libraries for networking
from socket import *
from pickle import *

#other module library
from random import *

#constant module
from ClientConstants import *

def start_client():       
    #create an instance of the display class and 
    #call it's mainloop to start the program
    display = Display()
    display.mainloop()

def get_game_code():
    #return the current game code value
    return game_code

class Display(Tk):

    def __init__(self):
        #make window 
        super().__init__()
        self.title("Exploding Kittens Online")
        self.iconphoto(True, PhotoImage(file = LOGO_IMAGE_PATH))
        self["bg"] = BG_COLOUR

        #set display size and configure the weight of the width and height
        self.geometry(f"{WIDTH}x{HEIGHT}")
        self.rowconfigure(0, weight = 1) 
        self.columnconfigure(0, weight = 1) 

        #create instance of client socket
        self.connection = Network(self)

        #create page stack
        self.page_stack = PageStack()

        #create dictionary of pages
        self.pages = {}
        for frame in (LoginPage, MenuPage, HostPage, LobbyPage, JoinPage, 
                      GamePage):
            page = frame(self)
            self.pages[str(page)] = page
            page.grid(row = 0, column = 0, sticky = N+E+S+W)

        #show login page
        login_page = self.pages["Login Page"]
        login_page.tkraise()

        #set up what to do if the window is closed
        self.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        #tell the server to close the client connection from the server-side
        command = {"command":"close"}
        self.connection.request(command)         
        
        #close the window and close the client connection
        self.destroy()
        self.connection.close()

    def forward(self, current_page_name, next_page_name):
        #show the next page in the program
        self.page_stack.push(current_page_name)
        next_page = self.pages[next_page_name]
        next_page.tkraise()

        #make updates to pages if needed
        if next_page_name == "Join Page":
            next_page.update_pub_games()

        elif next_page_name == "Lobby Page":
            next_page.update_code()
            next_page.updating = True
            next_page.update_player_list()

        elif next_page_name == "Game Page":
            next_page.set_up_page()

    def back(self):
        #show the previous page in the program
        prev_page_name = self.page_stack.pop()
        prev_page = self.pages[prev_page_name]
        prev_page.tkraise()

        #make updates to pages if needed
        if prev_page_name == "Join Page":
            prev_page.update_pub_games()

class Page(Frame):

    def __init__(self, parent, row_num, column_num):
        #inherit some of the parent's objects
        self.parent = parent
        self.connection = parent.connection

        #make page
        super().__init__()
        self["width"] = WIDTH
        self["height"] = HEIGHT
        self["bg"] = BG_COLOUR

        #configure the page grid
        self.grid_propagate(False)
        for row in range(row_num):
            self.rowconfigure(row, weight = 1) 
        for column in range(column_num):
            self.columnconfigure(column, weight = 1)

class LoginPage(Page):

    def __init__(self, parent):
        #set up page and grid
        super().__init__(parent, LOGIN_PAGE_ROWS, 7)
         
        #heading label
        Label(self, text = "Login", font = TITLE_FONT, relief = SUNKEN 
              ).grid(row = 0, column = 0, columnspan = 7, sticky = N+E+S+W)

        #login section
        Label(self, text = "Login", font = REGULAR_FONT
              ).grid(row = 1, column = 1, sticky = E+W)
        Label(self, text="Username:", font = REGULAR_FONT
              ).grid(row = 2, column = 0, ipadx = 1, padx = 2)
        self.ent_username = Entry(self, font = ENTRY_FONT_SIZE) 
        self.ent_username.grid(row = 2, column = 1, padx = 5)
        Label(self, text="Password:", font = REGULAR_FONT
              ).grid(row = 3, column = 0, ipadx = 1, padx = 1)
        self.ent_password = Entry(self, font = ENTRY_FONT_SIZE,  show = "*")
        self.ent_password.grid(row = 3, column = 1, padx = 5)
        Button(self, text = "Login", font = REGULAR_FONT, command = self.login
               ).grid(row = 3, column = 2, sticky = N)

        #seperator
        Label(self, bg = "black", width = 1
              ).grid(row = 1, column = 3, rowspan = LOGIN_PAGE_ROWS, padx = 5,
                     sticky = N+S)

        #create new account section
        Label(self, text = "Create a New Account", font = REGULAR_FONT
              ).grid(row = 1, column = 5, sticky = E+W)
        Label(self, text="Username:", font = REGULAR_FONT
              ).grid(row = 2, column = 4)
        self.ent_new_username = Entry(self, font = ENTRY_FONT_SIZE)
        self.ent_new_username.grid(row = 2, column = 5, padx = 5)
        Label(self, text="Password:", font = REGULAR_FONT
              ).grid(row = 3, column = 4)
        self.ent_new_password = Entry(self, font = ENTRY_FONT_SIZE,  show = "*")
        self.ent_new_password.grid(row = 3, column = 5, padx = 5)
        Button(self, text = "Register Account", font = REGULAR_FONT, 
               command = self.register
               ).grid(row = 3, column = 6, padx = 2, sticky = N)

    def __str__(self):
        return "Login Page"

    def login(self):
        #get username and password from the entry boxes
        username_input = self.ent_username.get()
        password_input = self.ent_password.get()

        #send a login request and the user data to the server
        command = {"command":"login", "user":username_input, "pswd":password_input}
        reply = self.connection.request(command)
        outcome = reply.decode()

        if outcome == "Success":
            global username
            username = username_input
            #move to the menu page if the user successfully made a new account
            self.parent.forward("Login Page", "Menu Page")

        else:
            #prompt user to retry if their username or password wasn't accepted
            messagebox.showerror(title = "Error", message = outcome)

        #clear the entry boxes
        self.ent_username.delete(0, "end")
        self.ent_password.delete(0, "end")

    def check_details(self, user, pswd):
        #user input validation
        #error message built based on errors raised by input
        error_message = ""
        if len(user) < 2 or len(user) > 10:
            error_message += "Username must be 2-10 characters long \n"

        if len(pswd) < 5 or len(pswd) > 15:
            error_message += "Password must be 5-15 characters long \n"

        if " " in user or " " in pswd:
            error_message += "Username and password must not contain spaces \n"
        
        #check for at least one capital letter and number in the password
        capital = False
        for character in pswd:
            if character.isupper():
                capital = True
                break
        number = False
        for character in pswd:
            if character.isnumeric():
                number = True
                break
        if not capital or not number:
            error_message += "Password must contain a capital letter and a number"

        #send the full error message 
        return error_message
     
    def register(self):
        #get username and password from the entry boxes
        username_input = self.ent_new_username.get()
        password_input = self.ent_new_password.get()

        #check if the user input is invalid
        invalid = self.check_details(username_input, password_input)
        if not invalid:
            #send a register request and the user data to the server
            command = {"command":"register", "user":username_input,
                       "pswd":password_input}
            reply = self.connection.request(command)
            outcome = reply.decode()

            if outcome == "Success":
                global username
                username = username_input
                #move to the menu page if the user successfully made a new account
                self.parent.forward("Login Page", "Menu Page")

            else:
                #prompt the user to retry if their username or password 
                #was already taken
                messagebox.showerror(title = "Error", message = outcome) 

        else:
            #prompt user to retry if their username or password wasn't valid
            messagebox.showerror(title = "Error", message = invalid)

        #clear entry boxes
        self.ent_new_username.delete(0, "end")
        self.ent_new_password.delete(0, "end")  
      
class MenuPage(Page):

    def __init__(self, parent):
        #set up page and grid
        super().__init__(parent, 6, 2)

        #heading label
        Label(self, text = "Menu", font = TITLE_FONT, relief = RIDGE
              ).grid(row = 0, column = 0, columnspan = 2, sticky = N+E+S+W)

        #menu options
        Button(self, text = "Host a Game", font = REGULAR_FONT, 
               command = lambda: parent.forward("Menu Page", "Host Page")
               ).grid(row = 1, column = 0, padx = 10, sticky = E+W)
        Button(self, text = "Join a Game", font = REGULAR_FONT,
               command = lambda: parent.forward("Menu Page", "Join Page")
               ).grid(row = 1, column = 1, padx = 10, sticky = E+W)
        Button(self, text = "Check Game Statistics", font = REGULAR_FONT, 
               command = self.check_stats
               ).grid(row = 2, column = 0, padx = 10, sticky = E+W)
        Button(self, text = "See Game Rules", font = REGULAR_FONT, 
               command = self.read_rules
               ).grid(row = 2, column = 1, padx = 10, sticky = E+W)

        #log out button
        Button(self, text = "Log Out", font = REGULAR_FONT, bg = BG_COLOUR, 
               command = self.log_out
               ).grid(row = 0, column = 0, padx = 5, pady = 5, sticky = N+W)

    def __str__(self):
        return "Menu Page"

    def check_stats(self):
        #ask the server to get the statistics from the User database
        command = {"command":"check stats"}
        reply = self.connection.request(command)
        stats = loads(reply)

        #make pop-up window and don't let its size be changed
        self.stats_window = Toplevel(bg = BG_COLOUR)
        self.stats_window.title("Games Statistics")
        self.stats_window.resizable(False, False)
        #the parent window can't be accessed without dealing with this one
        self.stats_window.grab_set() 

        #heading label
        Label(self.stats_window, text = "Game Statistics", font = TITLE_FONT, 
              relief = RIDGE
              ).grid(row = 0, column = 0, columnspan = 3, sticky = N+E+W+S)

        #show the user's game statistics
        stat_names = ("Games Played:", "Games Won:", "Win Streak:", "Games Lost:", 
                       "Exploding Kittens Drawn:", "Defuses Drawn:")
        for row in range(6):
            Label(self.stats_window, text = stat_names[row], font = REGULAR_FONT, 
                  bg = BG_COLOUR
                  ).grid(row = row + 1, column = 0, sticky = W)
            Label(self.stats_window, text = "\t", font = REGULAR_FONT, bg = BG_COLOUR
                  ).grid(row = row + 1, column = 1, sticky = W)
            Label(self.stats_window, text = stats[row], font = REGULAR_FONT, bg = BG_COLOUR
                  ).grid(row = row + 1, column = 2, sticky = E)

    def read_rules(self):
        #get rules from the server
        command = {"command":"read rules"}
        reply = self.connection.request(command)
        rules = reply.decode()

        #make window and don't let its size be changed
        self.rules_window = Toplevel(bg = BG_COLOUR)
        self.rules_window.title("Games Rules")
        self.rules_window.geometry("1000x500")
        self.rules_window.resizable(False, False)
        #the parent window can't be accessed without dealing with this one
        self.rules_window.grab_set() 
                       
        #heading label
        Label(self.rules_window, text = "Game Rules", font = TITLE_FONT, 
              relief = RIDGE
              ).pack(fill = X)

        #scrollable text box for the rules
        self.text_rules = scrolledtext.ScrolledText(self.rules_window, bg = BG_COLOUR, 
                                                    width = 1000, font = REGULAR_FONT)
        self.text_rules.pack()

        #output rules to the screen and don't allow the user to edit the text
        self.text_rules.insert(END, rules)
        self.text_rules.config(state = DISABLED)

    def log_out(self):
        #go back to the login page
        self.parent.back()

        #tell the server that the client has logged out
        command = {"command":"log out"}
        self.connection.request(command)

class HostPage(Page):

    def __init__(self, parent):
        #set up page and grid
        super().__init__(parent, 9, 2)

        #heading label
        Label(self, text = "Host a Game", font = TITLE_FONT, relief = RIDGE 
              ).grid(row = 0, column = 0, columnspan = 2, sticky = N+E+S+W)

        #show room type options
        Label(self, text = "Choose Game Room Type:", font = REGULAR_FONT, 
              bg = BG_COLOUR
              ).grid(row = 1, column = 0, columnspan = 2)
        Button(self, text = "Private", font = REGULAR_FONT,
               command = lambda: self.create_game("private")
               ).grid(row = 2, column = 0, padx = 10, sticky = E+W)
        Button(self, text = "Public", font = REGULAR_FONT,
               command = lambda: self.create_game("public")
               ).grid(row = 2, column = 1, padx = 10, sticky = E+W)

        #back button
        Button(self, text = "Back", font = REGULAR_FONT, bg = BG_COLOUR, 
               command = parent.back
               ).grid(row = 0, column = 0, padx = 5, pady = 5, sticky = N+W)

    def __str__(self):
        return "Host Page"

    def create_game(self, type):
        #ask the server to set up a game room and reply with its code
        command = {"command":"create game", "type":type}
        reply = self.connection.request(command)
        global game_code
        game_code = reply.decode()

        #enter the game lobby
        self.parent.forward("Host Page", "Lobby Page")

class JoinPage(Page):

    def __init__(self, parent):
        #set up page and grid
        super().__init__(parent, JOIN_PAGE_ROWS, 7)

        #heading label 
        Label(self, text = "Join a game", font = TITLE_FONT, relief = RIDGE 
              ).grid(row = 0, column = 0, columnspan = 7, sticky = N+E+S+W)

        #private game section
        Label(self, text = "Join a private game", font = REGULAR_FONT
             ).grid(row = 1, column = 1, sticky = E+W)
        Label(self, text="Enter room code:", font = REGULAR_FONT
              ).grid(row = 2, column = 0, padx = 2, sticky = N+E+W)
        self.ent_code = Entry(self, font = ENTRY_FONT_SIZE) 
        self.ent_code.grid(row = 2, column = 1, sticky = N)
        Button(self, text = "Go", font = REGULAR_FONT, command = self.join_priv
              ).grid(row = 2, column = 2, sticky = N)

        #seperator
        Label(self, bg = "black", width = 1
              ).grid(row = 1, column = 3, rowspan = JOIN_PAGE_ROWS, padx = 5, 
                     sticky = N+S)

        #public game section
        Label(self, text = "Join a Public Game", font = REGULAR_FONT
             ).grid(row = 1, column = 5, padx = 2, sticky = E+W)
        self.img_refresh = PhotoImage(file = REFRESH_IMAGE_PATH)
        Button(self, image = self.img_refresh, command = self.update_pub_games
               ).grid(row = 1, column = 6, padx = 2, sticky = E)
        Label(self, text = "Choose a Room:", font = REGULAR_FONT
             ).grid(row = 2, column = 4)
        self.lbl_no_pub_games = Label(self, text = "No public \n games available", 
                                      font = REGULAR_FONT)
        self.lbl_no_pub_games.grid(row = 2, column = 5, rowspan = 3, padx = 5, 
                                   sticky = N+S)
        
        #back button
        Button(self, text = "Back", font = REGULAR_FONT, bg = BG_COLOUR, 
               command = parent.back
               ).grid(row = 0, column = 0, padx = 5, pady = 5, sticky = N+W)

        #set up current public game buttons list 
        self.btns_pub_game = []

    def __str__(self):
        return "Join Page"

    def update_pub_games(self):
        #get public game code list from the server 
        command = {"command":"get pub games"}
        reply = self.connection.request(command)
        new_pub_games = loads(reply)

        #remove the old game code buttons then reset their list
        for button in self.btns_pub_game:
            button.grid_forget()
        self.btns_pub_game = []

        #update display if necessary
        if len(new_pub_games) == 0 and not self.lbl_no_pub_games.winfo_ismapped():
            #show the no games available label if it isn't already showing
            self.lbl_no_pub_games.grid(row = 2, column = 5, rowspan = 3, padx = 5, 
                                       sticky = N+S)

        elif len(new_pub_games) > 0:
            #remove the no game available label
            self.lbl_no_pub_games.grid_forget()

            #choose 6 random games to be shown at once
            shuffle(new_pub_games)
            new_pub_games = new_pub_games[:6]

            #show the chosen game rooms as buttons
            row = 2
            for game in new_pub_games:
                code = game[0]
                capacity = game[1]
                game_info = code + " \t " + str(capacity) + "/5"
                btn_pub_game = Button(self, text = game_info, font = SMALL_FONT,
                                      command = lambda cde = code: self.join_pub(cde))
                btn_pub_game.grid(row = row, column = 5, pady = 5)

                #put the buttons in a list so they can be ungridded 
                #when the page is updated 
                self.btns_pub_game.append(btn_pub_game)
                row += 1 

    def join_priv(self):
        #ask the server whether the entered code is valid
        code_input = self.ent_code.get()
        command = {"command":"join priv", "code":code_input}
        reply = self.connection.request(command)
        outcome = reply.decode()

        #enter the room if the code is valid
        if outcome == "Success":
            global game_code
            game_code = code_input
            self.parent.forward("Join Page", "Lobby Page")

        else:
            #otherwise, give an error message
            messagebox.showerror(title = "Error", message = outcome)

        #clear the entry box
        self.ent_code.delete(0, END)

    def join_pub(self, code):
        #ask the server whether the chosen room can still be joined
        command = {"command":"join pub", "code":code}
        reply = self.connection.request(command)
        outcome = reply.decode()

        #enter the room if the code is valid
        if outcome == "Success":
            global game_code
            game_code = code
            self.parent.forward("Join Page", "Lobby Page")

        else:
            messagebox.showerror(title = "Error", message = outcome)

        #clear the entry box (in case it was used)
        self.ent_code.delete(0, END)         

class LobbyPage(Page):

    def __init__(self, parent):
        #set up page and grid
        super().__init__(parent, 15, 3)

        #heading label
        Label(self, text = "Game Lobby", font = TITLE_FONT, relief = RIDGE 
              ).grid(row = 0, column = 0, columnspan = 3, sticky = N+E+S+W)

        #room code and current players labels
        self.lbl_code = Label(self, text = "Code:", font = REGULAR_FONT, 
                              bg = BG_COLOUR)
        self.lbl_code.grid(row = 1, column = 0, columnspan = 3)
        Label(self, text = "Players:", font = REGULAR_FONT, bg = BG_COLOUR
              ).grid(row = 2, column = 0, sticky = E) 

        #button to start the game
        self.btn_start = Button(self, text = "Start game", font = REGULAR_FONT, 
                                command = self.start_game)
        #back button
        Button(self, text = "Leave Game Room", font = REGULAR_FONT, bg = BG_COLOUR, 
               command = self.leave_room
               ).grid(row = 0, column = 0, padx = 5, pady = 5, sticky = N+W)

        #set up current player labels list and 
        #updating variable (tells the frame whether or not to keep updating)
        self.lbls_players = []
        self.updating = None

    def __str__(self):
        return "Lobby Page"

    def update_code(self):
        #update the code label to show the current code
        self.lbl_code["text"] = "Code: " + get_game_code()

    def update_player_list(self):
        #ask the server whether the game has started and for the current player list
        command = {"command":"update lobby"}
        reply = self.connection.request(command)
        outcome = loads(reply)
        new_player_list = outcome[0]
        room_status = outcome[1]

        #make updates if the player list has changed
        player_list = [label["text"] for label in self.lbls_players]
        if player_list != new_player_list:
            #remove the old player labels and reset their list
            for label in self.lbls_players:
                label.grid_forget()
            self.lbls_players = []

            #update and display the player list 
            row = 2
            for name in new_player_list:
                lbl_player = Label(self, text = name, font = REGULAR_FONT, 
                                   bg = BG_COLOUR)
                lbl_player.grid(row = row, column = 1)
                self.lbls_players.append(lbl_player)
                row += 1
 
        if room_status == "started":
            #if the host has started the game, tell the frame to stop updating 
            #the lobby and move the user to the game page 
            self.updating = False
            self.parent.forward("Lobby Page", "Game Page")

        elif not self.updating:
            #stops the recursion if the lobby has closed or 
            #the user has left the screen
            pass

        else:
            if room_status == "can start" and not self.btn_start.winfo_ismapped():
                #allow the host to start the game if there are enough players
                self.btn_start.grid(row = 2, column = 2, sticky = W)

            elif room_status == "waiting":
                #remove the start game button if there are no longer enough players 
                self.btn_start.grid_forget()

            #continue updating the lobby until the game starts
            self.after(1000, self.update_player_list)

    def start_game(self):
        #ask the server to start the game 
        command = {"command":"start game"}
        reply = self.connection.request(command)
        outcome = reply.decode()
        
        if outcome == "Success":
            #tell the frame to stop updating the lobby
            self.updating = False

            #move to the game page if the server can start the game 
            self.parent.forward("Lobby Page", "Game Page")

        else:
            #keep updating the lobby if there aren't enough players to start the game
            messagebox.showerror(title = "Error", 
                                 message = "There aren't enough players to start")

    def leave_room(self):
        #tell the frame to stop updating the lobby
        self.updating = False

        #tell the server that the client has left the room
        command = {"command":"leave room"}
        self.connection.request(command)

        #go back to the host or join room page
        self.parent.back()

class GamePage(Page):

    def __init__(self, parent):
        #set up page and grid
        super().__init__(parent, 5, 5)

        #set up draw and discard piles 
        self.img_deck = PhotoImage(file = DECK_IMAGE_PATH)
        self.btn_draw = Button(self, image = self.img_deck, state = DISABLED, 
                               command = self.draw)
        self.btn_draw.grid(row = 2, column = 2, pady = 5, sticky = N+E)
        self.lbl_discard_pile = Label(self, text = "Discard \n Pile", 
                                      font = REGULAR_FONT)
        self.lbl_discard_pile.grid(row = 2, column = 3, padx = 5, sticky = W)

        #set up label to show game updates
        self.lbl_updates = Label(self, font = REGULAR_FONT)
        self.lbl_updates.grid(row = 2, column = 1, sticky = E+W)

        #set up arrows to show the player order
        self.img_up_arrow = PhotoImage(file = UP_IMAGE_PATH)
        Label(self, image = self.img_up_arrow
              ).grid(row = 2, column = 0, sticky = S)
        self.img_down_arrow = PhotoImage(file = DOWN_IMAGE_PATH)
        Label(self, image = self.img_down_arrow
              ).grid(row = 2, column = 4, sticky = S)

        #set up the player label and picked cards lists
        self.lbls_player = []
        self.picked_cards = []

        #set up the user's name label and card submission button       
        lbl_player = Label(self, font = REGULAR_FONT)
        lbl_player.grid(row = 3, column = 1, columnspan = 2, sticky = S)
        self.lbls_player.append(lbl_player)
        self.btn_submit = Button(self, text = "Submit Cards", font = REGULAR_FONT,
                                 state = DISABLED, command = self.submit_cards) 
        self.btn_submit.grid(row = 3, column = 2, sticky = E)

        #set up the user's hand frame and its grid
        self.frm_hand = Frame(self, bg = BG_COLOUR, height = HAND_HEIGHT)
        self.frm_hand.grid(row = 4, column = 0, columnspan = 5, padx = 5, pady = 2, 
                           sticky = S+E+W)
        self.frm_hand.grid_propagate(False)
        for row in range(2):
            self.frm_hand.rowconfigure(row, weight = 1)
        for column in range(9):
            self.frm_hand.columnconfigure(column, weight = 1)

        #set up font to show whose turn it is
        self.turn_font = font.Font(family = "Comic Sans MS", size = 15, 
                                   weight = font.BOLD, underline = 1) 

    def __str__(self):
        return "Game Page"
  
    def set_up_page(self):
        #ask the server what to display in the game
        command = {"command":"set up game display"}
        reply = self.connection.request(command)
        details = loads(reply)

        #rearrange the player list so the user is first 
        players = details["players"]
        for i in range(len(players)):
            if players[i] == username:
                players = players[i:] + players[:i]
                #remove the user from the list to create a list of the other players 
                players.remove(username)
                self.other_players = players

                #display the other players
                self.img_hand = PhotoImage(file = HAND_IMAGE_PATH)
                col = 0
                for player in self.other_players:
                    Label(self, image = self.img_hand
                          ).grid(row = 0, column = col)
                    lbl_player = Label(self, text = player, font = REGULAR_FONT)
                    lbl_player.grid(row = 1, column = col)
                    self.lbls_player.append(lbl_player)                 
                    col += 1
                break

        #show the user's hand 
        self.lbls_player[0]["text"] = username
        self.hand = details["hand"]
        self.btns_hand = []
        self.update_hand()

        #start the game update loop
        self.update_page()

    def update_page(self, whose_turn = "", status = "", card_played = ""):
        if status != "ended":
            #ask the server for updates about what to display
            command = {"command":"update game"}
            reply = self.connection.request(command)
            updates = loads(reply)

            #update the discard pile if the last card played has changed
            if card_played != updates["card played"]:
                card_played = updates["card played"]
                self.update_discard_pile(card_played)

            #update player hand if it has changed
            if self.hand != updates["hand"]:
                self.hand = updates["hand"]
                self.update_hand()
                if whose_turn == username:
                    self.activate_buttons()

            #allow the user to have another go or 
            #end their turn if their current turn has ended
            if updates["turn over"] and username == whose_turn: 
                self.activate_buttons() 

            #change the updates label if there's a new update 
            if updates["new update"]:
                self.lbl_updates["text"] = updates["new update"]

            if whose_turn != updates["turn"]:
                #change player fonts to show who's turn it is if the turn changes 
                whose_turn = updates["turn"]
                for label in self.lbls_player:
                    if label["text"] == whose_turn:
                        label["font"] = self.turn_font

                    else: 
                        label["font"] = REGULAR_FONT

                #activate or disable the buttons depending on if it's the user's turn
                if whose_turn == username:
                    self.activate_buttons()

                else:
                    self.disable_buttons()

            if updates["can nope"]:
                #ask the player if they want to play their nope card 
                #and send their decision to the server
                nope_played = messagebox.askyesno(title = "Play Nope?", 
                                                  message = "Play your nope card?")
                command = {"command":"check nope", "noped":nope_played}
                self.connection.request(command)

            if updates["see the future"]:
                #show the future cards if the user played a see the future card
                self.see_future(updates["see the future"])

            if updates["choose card"]:
                #prompt the user to choose a card to give to another player
                self.show_card_chooser()

            #continue the loop until the game has ended
            status = updates["status"]
            self.after(1000, lambda: self.update_page(whose_turn, status, card_played))

        else:
            #disable all the buttons
            self.disable_buttons()

            #prompt the user to return to the menu page
            return_to_menu = messagebox.askyesno(title = "Game Over", 
                                              message = "The game is over. \n" \
                                                        "Return to the menu?")
            if return_to_menu:
                #pop pages from the stack until the menu page is reached
                current_page_name = str(self)
                while current_page_name != "Menu Page":
                    current_page_name = self.parent.page_stack.peek()
                    self.parent.back()

    def update_hand(self):
        #remove the old hand of cards and reset the hand buttons list
        for button in self.btns_hand:
            button.grid_forget()
        self.btns_hand = []

        #show the user's updated hand 
        self.imgs_card = []
        col = 0
        rw = 0
        index = 0
        for card_name in self.hand:
            #once 8 cards have been placed in the first row, move to the second
            if col == 8:
                rw += 1
                col = 0

            path = IMAGE_PATH + "/" + card_name + ".png"
            self.imgs_card.append(PhotoImage(file = path))
            btn_card = Button(self.frm_hand, image = self.imgs_card[index], 
                              text = card_name, state = DISABLED,
                              command = lambda pos = index: 
                              self.pick_card(self.btns_hand[pos]))
            btn_card.grid(row = rw, column = col)
            self.btns_hand.append(btn_card)
            col += 1
            index += 1

    def update_discard_pile(self, card_name):
        #change the card on top of the discard pile
        path = IMAGE_PATH + "/" + card_name + ".png"
        self.img_discard_card = PhotoImage(file = path)
        self.lbl_discard_pile["image"] = self.img_discard_card

    def activate_buttons(self):
        #allow buttons to be pressed and reset the list of picked cards
        self.btn_draw["state"] = NORMAL
        self.btn_submit["state"] = NORMAL
        for button in self.btns_hand:
            button["state"] = NORMAL
        self.picked_cards = []

    def disable_buttons(self):
        #disable all buttons
        self.btn_draw["state"] = DISABLED
        self.btn_submit["state"] = DISABLED
        for button in self.btns_hand:
            button["state"] = DISABLED  

    def do_nothing(self):
        #do nothing
        pass

    def pick_card(self, button):
        #add the chosen card to the list of picked cards 
        #and disable it so it can't be picked again
        self.picked_cards.append(button)
        button["state"] = DISABLED

    def submit_cards(self): 
        #disable all buttons
        self.disable_buttons()

        #make a list of the names of the cards the user wants to play
        cards = [button["text"] for button in self.picked_cards]

        #tell the server which cards the user wants to play
        command = {"command":"check cards", "cards":cards}
        reply = self.connection.request(command)
        outcome = reply.decode()

        #update the screen based on the outcome of the server request
        if outcome in ("Success", "Choose player"):
            #update the player's hand and the discard pile
            for card in cards:
                self.hand.remove(card)
            self.update_hand()
            self.update_discard_pile(cards[0])

            if outcome == "Choose player":
                #prompt the user to choose player to act against if needed
                self.show_player_chooser()
        else:
            #tell the user that their choice was invalid and let them try again
            self.lbl_updates["text"] = outcome
            self.activate_buttons()             

    def show_player_chooser(self):
        #create a window
        self.chooser_window = Toplevel(bg = BG_COLOUR)
        self.chooser_window.title("Player Chooser")
        #the parent window can't be accessed without dealing with this one
        self.chooser_window.grab_set() 
        #don't let the 'X' button be used to close the window
        self.chooser_window.protocol("WM_DELETE_WINDOW", self.do_nothing)

        #instruction label
        Label(self.chooser_window, text = "Choose a player to take cards from:", 
              font = REGULAR_FONT, bg = BG_COLOUR
              ).pack(fill = X)

        #put buttons with the other players' names on them in the window
        for player in self.other_players:
            Button(self.chooser_window, text = player, font = SMALL_FONT,
                   command = lambda name = player: self.choose_player(name)
                   ).pack(fill = X)

    def choose_player(self, player):
        #when a button in the player chooser window is pressed the window's destroyed 
        self.chooser_window.destroy()

        #inform the server of the player's choice
        command = {"command":"choose player", "player":player}
        self.connection.request(command)

    def show_card_chooser(self):
        #create a window
        self.card_window = Toplevel(bg = BG_COLOUR)
        self.card_window.title("Card Chooser")
        #the parent window can't be accessed without dealing with this one
        self.card_window.grab_set() 
        #don't let the 'X' button be used to close the window
        self.card_window.protocol("WM_DELETE_WINDOW", self.do_nothing)

        #instruction label
        Label(self.card_window, text = "Choose a card to give away:", 
              font = REGULAR_FONT, bg = BG_COLOUR
              ).pack(fill = X)

        #put buttons with the player's card names on them in the window
        for card in self.hand:
            Button(self.card_window, text = card, font = SMALL_FONT,
                   command = lambda chosen_card = card: self.choose_card(chosen_card)
                   ).pack(fill = X)

    def choose_card(self, card):
        #when a button in the card chooser window is pressed the window's destroyed 
        self.card_window.destroy()

        #inform the server of the player's choice
        command = {"command":"choose card", "card":card}
        self.connection.request(command)

    def see_future(self, cards):
        #create a window
        self.cards_window = Toplevel(bg = BG_COLOUR)
        self.cards_window.title("See the Future")
        self.cards_window.resizable(False, False)

        #heading label
        Label(self.cards_window, text = "The 3 Cards on Top of the Deck:", 
              font = REGULAR_FONT, bg = BG_COLOUR
              ).grid(row = 0, column = 0, columnspan = 3, sticky = E+W)

        #show the top 3 cards on the deck
        self.imgs_future_card = []
        col = 0
        for card_name in cards:
            path = IMAGE_PATH + "/" + card_name + ".png"
            self.imgs_future_card.append(PhotoImage(file = path))
            Label(self.cards_window, image = self.imgs_future_card[col]
                  ).grid(row = 1, column = col)
            col += 1

    def draw(self):
        #drawing a card ends the player's turn so their buttons are disabled
        self.disable_buttons()

        #ask the server to draw the card on top of the deck 
        command = {"command":"draw card"}
        reply = self.connection.request(command)
        outcome = reply.decode()
        
        #inform the user if they've drawn an exploding kitten
        if outcome == "Defuse":
            self.show_ek_window(False)
        elif outcome == "No Defuse":
            self.show_ek_window(True)  

    def show_ek_window(self, dead):
        #create a window
        self.ek_window = Toplevel(bg = BG_COLOUR)
        self.ek_window.title("Exploding Kitten")
        #the parent window can't be accessed without dealing with this one
        self.ek_window.grab_set() 
        #don't let the 'X' button be used to close the window
        self.ek_window.protocol("WM_DELETE_WINDOW", self.do_nothing)

        #tell the user that they drew an exploding kitten
        Label(self.ek_window, text = "You Drew an Exploding Kitten...", 
              font = REGULAR_FONT
              ).grid(row = 0, column = 0, columnspan = 3, sticky = E+W) 
        self.img_ek = PhotoImage(file = "Images/Exploding Kitten.png")
        Label(self.ek_window, image = self.img_ek
              ).grid(row = 1, column = 0, rowspan = 2)

        #tell the user whether they died or not
        if dead:
            Label(self.ek_window, text = "You don't have a defuse \n so you blew up!", 
                  font = REGULAR_FONT, bg = BG_COLOUR
                  ).grid(row = 1, column = 1)
            Button(self.ek_window, text = "Continue", font = REGULAR_FONT, 
                   command = self.accept_death
                   ).grid(row = 2, column = 1)
        else:
            #ask the server for the number of cards in the remaining deck
            command = {"command":"count deck"}
            reply = self.connection.request(command)
            card_num = int(reply.decode())

            #prompt the player to choose where to put the exploding kitten 
            #back into the deck 
            Label(self.ek_window, font = REGULAR_FONT, bg = BG_COLOUR,
                  text = "You have a defuse \n so choose where to put" \
                         "\n the Exploding Kitten:"
                 ).grid(row = 1, column = 1, columnspan = 2)
            self.sb_position = Spinbox(self.ek_window, from_ = 1, to = card_num, 
                                       state = "readonly", font = REGULAR_FONT)
            self.sb_position.grid(row = 2, column = 1, padx = 5)
            Button(self.ek_window, text = "Go", font = REGULAR_FONT,
                   command = self.place_kitten
                   ).grid(row = 2, column = 2, padx = 2)

    def accept_death(self):
        #destroy the ek window 
        #and tell the server that the user has received the message
        self.ek_window.destroy()
        command = {"command":"accept death"}
        self.connection.request(command)

    def place_kitten(self):
        #tell the server where to put the exploding kitten and destroy the ek window 
        command = {"command":"place kitten", "position": self.sb_position.get()}
        self.connection.request(command)
        self.ek_window.destroy()

class PageStack:

    def __init__(self):
        #set up the stack
        self.stack = []

    def push(self, page_name):
        #put the chosen page on top of the stack
        self.stack.append(page_name)
    
    def pop(self):
        #remove and return the page on top of the stack 
        return self.stack.pop()

    def peek(self):
        #return the page on top of the stack
        return self.stack[-1]

class Network(socket):

    def __init__(self, display):
       #create a record of the display so it can be referenced with in the class
       self.display = display

       #create the client socket and try to connect to the game server
       super().__init__()
       try:
           self.connect((SERVER_IP, SERVER_PORT))
       except:
           self.handle_error()

    def request(self, data):
        #send data to the server and receive a reply
        try: 
            self.sendall(dumps(data))
            reply = self.recv(4096)
            return reply
        except:
            #handle any connection error
            self.handle_error()
            
    def handle_error(self):
        if self.display.winfo_exists():
            #prompt user to end the program if the game server is down 
            #and the window hasn't already been closed
            end = messagebox.askyesno(title = "Error", message = "Game server is" \
                 " down. \n Close program?")
            if end:
                #destroy the window
                self.display.destroy()

#start the program
start_client()
