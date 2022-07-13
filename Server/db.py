import mysql.connector as db
dbu = db.connect(host="localhost", user="isobel", password="exploding", database="User")
cursor = dbu.cursor()

sql = "DELETE FROM User WHERE username LIKE 'username%'"
cursor.execute(sql)
dbu.commit()

sql = "SELECT Username, Password FROM User"
cursor.execute(sql)
user_result = cursor.fetchall()
for result in user_result:
    print("Username:",result[0],"Password:",result[1])
a = input("...")
