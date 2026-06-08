import os
import io
import re
import pickle
import mimetypes
import custom_logger
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path


class GoogleDriveDownloader:
    SCOPES = ['https://www.googleapis.com/auth/drive']
    UPLOAD_CHUNK_SIZE = 5 * 1024 * 1024  # 5 MB
    EXPORT_MAP = {
        'application/vnd.google-apps.document':     ('application/pdf', '.pdf'),
        'application/vnd.google-apps.spreadsheet':  ('application/pdf', '.pdf'),
        'application/vnd.google-apps.presentation': ('application/pdf', '.pdf'),
        'application/vnd.google-apps.drawing':      ('application/pdf', '.pdf'),
        'application/vnd.google-apps.form':         ('application/pdf', '.pdf'),
    }

    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.pickle'):
        self.__credentials_file = credentials_file
        self.__token_file = token_file
        self.__logger = custom_logger.get_logger("GoogleDriveDownloader")
        self.service = None

    # ------------------------------------------------------------------ #
    #  Authentication                                                       #
    # ------------------------------------------------------------------ #

    def authenticate(self):
        """Authenticates with Google Drive and initialises the service client."""
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

        creds = None

        if os.path.exists(self.__token_file):
            with open(self.__token_file, 'rb') as token:
                creds = pickle.load(token)
            self.__logger.debug("Loaded cached credentials from '%s'.", self.__token_file)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                self.__logger.info("Credentials expired — refreshing...")
                creds.refresh(Request())
                self.__logger.info("Credentials refreshed successfully.")
            else:
                self.__logger.info("No valid credentials found — starting OAuth flow.")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.__credentials_file,
                    self.SCOPES
                )
                flow.redirect_uri = 'http://localhost:8080/'
                auth_url, _ = flow.authorization_url(prompt='consent')

                self.__logger.info("OAuth authorisation URL generated.")
                self.__logger.info("=" * 70)
                self.__logger.info("1. Copy and open this link in your browser:")
                self.__logger.info(auth_url)
                self.__logger.info("2. After authorization you will see 'Unable to connect' or 'Site can't be reached'.")
                self.__logger.info("3. COPY THE FULL URL from the address bar (it will start with localhost:8080...)")
                self.__logger.info("=" * 70)

                auth_response = input("Paste the copied URL here: ").strip()
                self.__logger.debug("Auth response received from user.")

                if auth_response.startswith('https://localhost'):
                    auth_response = auth_response.replace('https://localhost', 'http://localhost', 1)
                    self.__logger.debug("Replaced https://localhost with http://localhost in auth response.")

                flow.fetch_token(authorization_response=auth_response)
                creds = flow.credentials
                self.__logger.info("OAuth flow completed successfully.")

            with open(self.__token_file, 'wb') as token:
                pickle.dump(creds, token)
            self.__logger.debug("Credentials saved to '%s'.", self.__token_file)

        self.service = build('drive', 'v3', credentials=creds)
        self.__logger.info("Google Drive service initialised.")
        return self

    # ------------------------------------------------------------------ #
    #  Public: download                                                     #
    # ------------------------------------------------------------------ #

    def download(self, link: str, dest_folder: str = '.'):
        """
        Downloads a file or an entire folder from a Google Drive link.

        Args:
            link:        Any Google Drive share URL (file or folder).
            dest_folder: Local destination directory (default: current directory).
        """
        if self.service is None:
            raise RuntimeError("Call authenticate() before download().")

        resource_id, resource_type = self._extract_id_from_link(link)
        self.__logger.info("Detected %s with ID: %s", resource_type, resource_id)

        if resource_type == 'folder':
            self._download_folder(resource_id, dest_folder)
        else:
            meta = self.service.files().get(fileId=resource_id, fields='name').execute()
            self._download_file(resource_id, meta['name'], dest_folder)

        self.__logger.info("Download finished.")

    # ------------------------------------------------------------------ #
    #  Private: download helpers                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_id_from_link(link: str) -> tuple[str, str]:
        """Returns (id, 'file'|'folder') from any common Google Drive URL."""
        folder_patterns = [
            r'drive\.google\.com/drive(?:/u/\d+)?/folders/([a-zA-Z0-9_-]+)',
        ]
        for pattern in folder_patterns:
            match = re.search(pattern, link)
            if match:
                return match.group(1), 'folder'

        file_patterns = [
            r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
            r'drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
            r'drive\.google\.com/uc\?id=([a-zA-Z0-9_-]+)',
            r'[?&]id=([a-zA-Z0-9_-]+)',
        ]
        for pattern in file_patterns:
            match = re.search(pattern, link)
            if match:
                return match.group(1), 'file'

        raise ValueError(f"Could not extract a Drive ID from: {link}")

    def _download_file(self, file_id: str, file_name: str, dest_folder: str):
        """Downloads a single file, exporting Google Workspace formats as PDF."""
        os.makedirs(dest_folder, exist_ok=True)

        meta = self.service.files().get(fileId=file_id, fields='mimeType').execute()
        mime_type = meta['mimeType']
        dest_path = os.path.join(dest_folder, file_name)

        if mime_type in self.EXPORT_MAP:
            export_mime, ext = self.EXPORT_MAP[mime_type]
            if not dest_path.endswith(ext):
                dest_path += ext
            request = self.service.files().export_media(fileId=file_id, mimeType=export_mime)
            self.__logger.debug("Exporting Workspace file '%s' as %s.", file_name, ext)

        elif mime_type.startswith('application/vnd.google-apps'):
            self.__logger.warning(
                "Skipping unsupported Workspace file: '%s' (%s).", file_name, mime_type
            )
            return

        else:
            request = self.service.files().get_media(fileId=file_id)

        self.__logger.info("Downloading '%s' -> '%s'", file_name, dest_path)
        try:
            with io.FileIO(dest_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    self.__logger.debug("'%s' — %d%%", file_name, int(status.progress() * 100))
        except Exception as e:
            self.__logger.error("Failed to download '%s': %s", file_name, e, exc_info=True)
            raise

        self.__logger.info("'%s' downloaded successfully.", file_name)

    def _download_folder(self, folder_id: str, dest_folder: str):
        """Recursively downloads a Drive folder, preserving its structure."""
        meta = self.service.files().get(fileId=folder_id, fields='name').execute()
        folder_name = meta['name']
        local_path = os.path.join(dest_folder, folder_name)
        os.makedirs(local_path, exist_ok=True)
        self.__logger.info("Downloading folder '%s' -> '%s'", folder_name, local_path)
        self._download_folder_contents(folder_id, local_path)

    def _download_folder_contents(self, folder_id: str, local_path: str):
        """Lists and downloads every item inside a folder (called recursively)."""
        page_token = None
        while True:
            response = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields='nextPageToken, files(id, name, mimeType)',
                pageToken=page_token
            ).execute()

            for item in response.get('files', []):
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    sub_path = os.path.join(local_path, item['name'])
                    os.makedirs(sub_path, exist_ok=True)
                    self.__logger.info("Entering subfolder: '%s'", item['name'])
                    self._download_folder_contents(item['id'], sub_path)
                else:
                    self._download_file(item['id'], item['name'], local_path)

            page_token = response.get('nextPageToken')
            if not page_token:
                break

    # ------------------------------------------------------------------ #
    #  Public: upload                                                       #
    # ------------------------------------------------------------------ #

    def upload(self, local_path: str, drive_folder_link: str = None):
        """
        Uploads a file or an entire directory to Google Drive.

        Args:
            local_path:        Path to a local file or directory.
            drive_folder_link: Optional Drive folder link to upload into.
                               If None, uploads to the root of My Drive.
        """
        if self.service is None:
            raise RuntimeError("Call authenticate() before upload().")

        parent_id = None
        if drive_folder_link:
            parent_id, resource_type = self._extract_id_from_link(drive_folder_link)
            if resource_type != 'folder':
                raise ValueError("drive_folder_link must point to a folder, not a file.")
            self.__logger.debug("Upload destination folder ID: %s", parent_id)
        else:
            self.__logger.debug("No destination folder specified — uploading to Drive root.")

        local_path = os.path.abspath(local_path)
        self.__logger.info("Resolved local path: '%s'", local_path)

        if os.path.isfile(local_path):
            self._upload_file(local_path, parent_id)
        elif os.path.isdir(local_path):
            self._upload_directory(local_path, parent_id)
        else:
            self.__logger.error("Path does not exist: '%s'", local_path)
            raise ValueError(f"Path does not exist: {local_path}")

        self.__logger.info("Upload complete.")

    # ------------------------------------------------------------------ #
    #  Private: upload helpers                                              #
    # ------------------------------------------------------------------ #

    def _upload_file(self, file_path: str, parent_id: str = None) -> str:
        """Uploads a single file to Drive. Returns the new Drive file ID."""
        file_name = os.path.basename(file_path)
        mime_type = self._guess_mime_type(file_path)
        self.__logger.debug("Guessed MIME type for '%s': %s", file_name, mime_type)

        metadata = {'name': file_name}
        if parent_id:
            metadata['parents'] = [parent_id]

        media = MediaFileUpload(file_path, mimetype=mime_type,
                                chunksize=self.UPLOAD_CHUNK_SIZE, resumable=True)

        self.__logger.info("Uploading '%s' (MIME: %s)", file_path, mime_type)
        request = self.service.files().create(body=metadata, media_body=media, fields='id')

        try:
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    self.__logger.debug("'%s' — %d%%", file_name, int(status.progress() * 100))
        except Exception as e:
            self.__logger.error("Failed to upload '%s': %s", file_name, e, exc_info=True)
            raise

        file_id = response.get('id')
        self.__logger.info("'%s' uploaded successfully. Drive ID: %s", file_name, file_id)
        return file_id

    def _upload_directory(self, dir_path: str, parent_id: str = None):
        """Recursively uploads a local directory, preserving its structure."""
        dir_name = os.path.basename(dir_path)
        self.__logger.info("Preparing to upload directory '%s'", dir_name)
        folder_id = self._create_drive_folder(dir_name, parent_id)
        self.__logger.info("Created Drive folder '%s' (ID: %s)", dir_name, folder_id)

        entries = list(os.scandir(dir_path))
        self.__logger.debug("Found %d entries in '%s'.", len(entries), dir_path)

        for entry in entries:
            if entry.is_file():
                self._upload_file(entry.path, folder_id)
            elif entry.is_dir():
                self.__logger.info("Descending into subdirectory '%s'.", entry.name)
                self._upload_directory(entry.path, folder_id)
            else:
                self.__logger.warning("Skipping unrecognised entry: '%s'", entry.path)

    def _create_drive_folder(self, name: str, parent_id: str = None) -> str:
        """Creates a folder on Drive and returns its ID."""
        self.__logger.debug("Creating Drive folder '%s' (parent: %s).", name, parent_id or 'root')
        metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            metadata['parents'] = [parent_id]

        try:
            folder = self.service.files().create(body=metadata, fields='id').execute()
        except Exception as e:
            self.__logger.error("Failed to create Drive folder '%s': %s", name, e, exc_info=True)
            raise

        return folder['id']

    @staticmethod
    def _guess_mime_type(file_path: str) -> str:
        """Returns a MIME type for the file, falling back to octet-stream."""
        mime, _ = mimetypes.guess_type(file_path)
        return mime or 'application/octet-stream'




# ------------------------------------------------------------------ #
#  AUTHENTIFICATION IS THE SAME FOR ALL                                            #
# ------------------------------------------------------------------ #


downloader = GoogleDriveDownloader(
    credentials_file='/home/kris/work/Ukrainian-Dictionary-Parser/utils/secrets/google_drive_creds.json',
    token_file='token.pickle'
)

downloader.authenticate()

# ------------------------------------------------------------------ #
#  TESTING THE DOWNLOADING                                            #
# ------------------------------------------------------------------ #

#downloader.download(
 #    link="https://drive.google.com/drive/folders/1lKmc6MpT8d8DCOLQxsyLv6BxQvUFVmUh?usp=sharing",
  #   dest_folder="/home/kris/work/Ukrainian-Dictionary-Parser/data/downloads/"
 #)

# ------------------------------------------------------------------ #
#  TESTING THE UPLOADING                                            #
# ------------------------------------------------------------------ #


downloader.upload(
     local_path="/home/kris/work/Ukrainian-Dictionary-Parser/data/output",
     drive_folder_link="https://drive.google.com/drive/folders/1lKmc6MpT8d8DCOLQxsyLv6BxQvUFVmUh?usp=drive_link"  # optional
 )
