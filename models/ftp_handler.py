from ftplib import FTP_TLS
 
    
class FTPHandler:
    def __init__(self, server, username, password):
        self.server = server
        self.username = username
        self.password = password

    def download_file(self, remote_file_path, local_file_path):
        try:
            with FTP_TLS(self.server) as ftp:
                ftp.login(user=self.username, passwd=self.password)
                ftp.prot_p()
                with open(local_file_path, 'wb') as local_file:
                    ftp.retrbinary(f"RETR {remote_file_path}", local_file.write)
        except Exception as e:
            print(f"FTP Download Error: {e}")