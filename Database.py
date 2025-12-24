from . import Operasi
DB_NAME = "data.txt"
TEMPLATE = {
    "pk":"XXXXXX",
    "date_add":"yyyy-mm-dd",
    "judul":255*" ",
    "penulis":255*" ",
    "tahun":"yyyy"
}

def init_console():
    try:
        with open(DB_NAME,"r") as file:
            print("Database Tersedia, init done!")

    except:
        print("Database Tidak ditemuka, silahkan membuat data baru")
        Operasi.create_first_data()
            