import sqlite3
import hashlib 

conn = sqlite3.connect("userdata.db")
cur = conn.cursor()

def p():
  output = cur.fetchall() 
  for row in output: 
    print(row) 

def col():
  cur.execute("""
  PRAGMA TABLE_INFO('userdata');
  """)
  p()

cur.execute("""
DROP TABLE userdata         
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS userdata(
    id INTEGER PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    rgb_mapping VARCHAR(511) NOT NULL
)           
""")

# cur.execute("""
# UPDATE userdata
# SET username = 'Dav', password = ?
# WHERE id = 1;  
# """, [hashlib.sha256("12345678".encode()).hexdigest()])



rgb1 = '#ffffff' * 48
username1, password1= "Mike", hashlib.sha256("12345678".encode()).hexdigest()
# username2, password2 = "Dav", hashlib.sha256("aPassword".encode()).hexdigest()
# username3, password3 = "Nate", hashlib.sha256(f"79wa9__dwaE98".encode()).hexdigest()
# username4, password4 = "John", hashlib.sha256("1@ad45a78A".encode()).hexdigest()
# cur.execute("INSERT INTO userdata (username, password, rgb_mapping) VALUES (?,?,?)", (username1, password1, rgb1))
# cur.execute("INSERT INTO userdata (username, password) VALUES (?,?)", (username2, password2))
# cur.execute("INSERT INTO userdata (username, password) VALUES (?,?)", (username3, password3))
# cur.execute("INSERT INTO userdata (username, password) VALUES (?,?)", (username4, password4))

cur.execute("""
SELECT * FROM userdata     
""")
p()



conn.commit()
conn.close()