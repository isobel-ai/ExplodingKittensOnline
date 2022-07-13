# ExplodingKittensOnline
A server-client multiplayer implementation of the card game Exploding Kittens. 

On the client-side the user can login, start (or join) a game and play with others, as well as check their game statistics. All these processes are facilitated by the server-side of the system, which the client connects to when the program starts-up. The server hosts the games and connects to both the user database (a MySQL database), which holds the user’s login details and game statistics, and a file containing the game rules.
