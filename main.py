from ftplib import FTP, error_perm, error_reply, error_temp, error_proto
import os
import logging

LOCAL_PDF_DIR = "./PDFs"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("ftp_download.log")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


def is_file(ftp, path):
    """
    Return True if `path` is a file on FTP server, False otherwise.
    We use FTP.size() - if it returns size, it's a file.
    """
    try:
        size = ftp.size(path)
        if size is not None:
            return True
        return False
    except (error_perm, error_reply, error_temp, error_proto):
        # If FTP doesn't support SIZE or path is a directory, an error is thrown
        return False
    except Exception as e:
        logging.error(f"Unexpected error in is_file checking {path}: {e}")
        return False


def is_directory(ftp, path):
    """
    Return True if path is a directory.
    We try to cwd into it; if success, it's a directory.
    """
    current = ftp.pwd()
    try:
        ftp.cwd(path)
        ftp.cwd(current)
        return True
    except Exception:
        return False


def sanitize_filename(path):
    return path.strip("/").replace("/", "_")


def download_pdf_files(ftp, remote_dir):
    try:
        ftp.cwd(remote_dir)
        items = ftp.nlst()
    except Exception as e:
        logging.error(f"Failed to list directory: {remote_dir} — {e}")
        return

    for item in items:
        if item in (".", ".."):
            continue

        remote_path = f"{remote_dir}/{item}".replace("//", "/")

        try:
            if is_file(ftp, remote_path):
                # It's a file, check extension
                if item.lower().endswith(".pdf"):
                    os.makedirs(LOCAL_PDF_DIR, exist_ok=True)
                    local_filename = sanitize_filename(remote_path)
                    local_path = os.path.join(LOCAL_PDF_DIR, local_filename)
                    with open(local_path, "wb") as f:
                        logging.info(f"Downloading file: {remote_path} → {local_path}")
                        ftp.retrbinary(f"RETR {remote_path}", f.write)
                else:
                    # It's a non-PDF file; skip silently
                    logging.debug(f"Skipping non-PDF file: {remote_path}")

            elif is_directory(ftp, remote_path):
                logging.info(f"Entering directory: {remote_path}")
                try:
                    download_pdf_files(ftp, remote_path)
                except Exception as e:
                    logging.error(f"Error recursing into {remote_path}: {e}")

            else:
                # Neither file nor directory, skip
                logging.debug(f"Skipping unknown type: {remote_path}")

        except Exception as e:
            logging.error(f"Error processing {remote_path}: {e}")


def main():
    try:
        ftp = FTP("ftp.ncbi.nlm.nih.gov")
        ftp.login()
        logging.info("Connected to ftp.ncbi.nlm.nih.gov")

        download_pdf_files(ftp, "/")

        ftp.quit()
        logging.info("Download completed successfully.")
    except Exception as e:
        logging.critical(f"Critical error in main(): {e}")


if __name__ == "__main__":
    main()
