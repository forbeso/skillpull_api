import ast
from io import BytesIO
from flask import Flask, jsonify, request
import utils
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
import tempfile
import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy.spiders import Spider
from twisted.internet import reactor, defer
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


class StorageException(Exception):
    def __init__(self, status_code, error, message):
        self.status_code = status_code
        self.error = error
        self.message = message


# app.config.update(
#     DEBUG=True,
#     SECRET_KEY="dev",
#     SESSION_COOKIE_HTTPONLY=True,
#     REMEMBER_COOKIE_HTTPONLY=True,
#     SESSION_COOKIE_SAMESITE="Strict",
# )


@app.route("/")
def hello_world():
    return "<p>Job Fill Chrome Extension</p>"


# User Management
# Flask backend
from flask import json
from datetime import datetime


# Function to convert datetime to string
def serialize_datetime(obj):
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return obj


@app.route("/login", methods=["POST"])
def login():
    logging.info(msg="Entered LOGIN function")
    try:
        data = request.json

        resp = supabase.auth.sign_in_with_password(
            {"email": data["email"], "password": data["password"]}
        )

        logging.info(msg=f'email: {data["email"]}, password: {data["password"]}')
        user_iden = resp.user.identities[0]

        # Serialize the user_iden object
        user_iden_dict = {
            "id": user_iden.id,
            "user_id": user_iden.user_id,
            "identity_data": user_iden.identity_data,
            "provider": user_iden.provider,
            "created_at": user_iden.created_at,
            "last_sign_in_at": user_iden.last_sign_in_at,
            "updated_at": user_iden.updated_at,
        }

        # Convert to JSON string with custom serialization
        user_iden_json = json.dumps(user_iden_dict, default=serialize_datetime)

        # Extract necessary information from the user object
        user_data = {
            "email": resp.user.email,
            "name": "",
            "identities": json.loads(user_iden_json),  # Deserialize the JSON string
        }

        session_data = {
            "access_token": resp.session.access_token,
        }

        return jsonify({"message": {"user": user_data, "session": session_data}})
    except Exception as e:
        logging.error(f"Error logging in: {e}")
        return jsonify({"message": "Error logging in."}), 500


@app.route("/register", methods=["POST"])
def register():
    logging.info(msg="Entered REGISTRATION function")
    try:
        data = request.json
        # Validate email format and password length
        # if not is_valid_email(data["email"]) or len(data["password"]) < 8:
        #     return jsonify({"message": "Invalid email address or password."}), 400

        # Attempt registration
        resp = supabase.auth.sign_up(
            {
                "email": data["email"],
                "password": data["password"],
                "options": {
                    "data": {
                        "first_name": data.get("first_name"),
                        "age": data.get("age"),
                    }
                },
            }
        )
        print(resp)
        # return str(resp)
        return jsonify(
            {
                "message": {
                    "user": {
                        "email": resp.user.email,
                        "access_token": resp.session.access_token,
                    }
                }
            }
        )
    except Exception as e:
        logging.error(f"Error registering: {e}")
        return jsonify({"message": f"Error registering. {e}"}), 500


@app.route("/user/data")
def get_user_data():
    jwt = ""
    data = supabase.auth.get_user(jwt)
    return "<p>Job Fill Chrome Extension</p>"


@app.route("/user/get-session")
def get_session():
    try:
        sess = supabase.auth.get_session()
        print(sess)
        if sess != None:
            return (
                jsonify(
                    {
                        "message": "active",
                        "atoken": sess.access_token,
                        "user_id": sess.user.identities[0].user_id,
                    }
                ),
                200,
            )
        else:
            return jsonify({"message": "Inactive", "atoken": ""}), 404

    except Exception as e:
        logging.error(f"Error getting user session: {e}")
        return jsonify({"message": f"Error getting user session. {e}"}), 500


@app.route("/user/logout")
def logout():
    return "<p>Job Fill Chrome Extension</p>"


# Resume Management


@app.route("/upload-resume", methods=["POST"])
def upload_resume():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        uploaded_file = request.files["file"]
        allowed_extensions = ["docx", "pdf"]

        # get file extension
        extension = uploaded_file.filename.split(".")[-1].lower()

        # check filetype is allowed
        if extension not in allowed_extensions:
            return jsonify({"error": "Unsupported file format"}), 415

        # Save file
        contents = uploaded_file.read()

        # if user is logged in save to supabase
        session_response = get_session()

        if session_response[0].status_code == 200:
            # Access user_id from the session response
            session_data = session_response[0].data
            x = json.loads(session_data)
            user_id = x.get("user_id")

            if user_id:
                # Save file to Supabase storage using user ID and file name
                result = supabase.storage.from_("file_ress").upload(
                    file=contents,
                    path=f"resumes/{uploaded_file.filename}",
                    file_options={"content-type": "application/pdf"},
                )

                return jsonify({"message": result.status_code}), 201

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@app.route("/get-resumes", methods=["GET"])
def get_resumes():
    try:
        # Get the bucket name from the request (e.g., query parameter, header)
        # bucket_name = request.args.get("bucket_name")

        # List files in the bucket
        files = supabase.storage.from_("files").list()
        # len(files)
        # Prepare the response data
        data = {"files": [{i: file} for i, file in enumerate(files)]}

        return jsonify(data)
    except Exception as e:
        logging.error(f"Error listing files: {e}")
        return jsonify({"message": "Error listing files."}), 500


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


def scrape_form_fields(url):
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")

        # Extract names or IDs of form fields
        form_fields = [
            field.get("name") or field.get("id") for field in soup.select("form input")
        ]

        return form_fields

    except Exception as e:
        logging.error(f"Error: {e}")
        raise


@app.route("/scrape-form-fields", methods=["POST"])
def scrape_form_fields_route():
    try:
        data = request.json
        url = data.get("url")

        if not url:
            return jsonify({"error": "Missing URL parameter"}), 400

        # Scrape the form fields
        form_fields_result = scrape_form_fields(url)

        # Log the results
        logging.info(f"Form Fields Result: {form_fields_result}")

        return jsonify({"form_fields": form_fields_result})

    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/get-resume/<resume_id>")
def get_resume_by_id():
    return "<p>Job Fill Chrome Extension</p>"


@app.route("/delete-resume/<resume_id>")
def delete_resume_by_id():
    return "<p>Job Fill Chrome Extension</p>"


# Form Processing


@app.route("/extract-form-fields")
def extract_form_fields():
    return "<p>Job Fill Chrome Extension</p>"


@app.route("/match-form-fields")
def match_form_fields():
    return "<p>Job Fill Chrome Extension</p>"


if __name__ == "__main__":
    app.run(threaded=True, debug=True)
