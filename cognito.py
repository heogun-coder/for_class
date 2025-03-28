from flask import Flask, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Use a secure random key in production
oauth = OAuth(app)

oauth.register(
    name="oidc",
    authority="https://cognito-idp.us-east-2.amazonaws.com/us-east-2_EBA96hq4a",
    client_id="1dompom8s0t0sf89h1h5ctbgp",
    client_secret="<client secret>",
    server_metadata_url="https://cognito-idp.us-east-2.amazonaws.com/us-east-2_EBA96hq4a/.well-known/openid-configuration",
    client_kwargs={"scope": "phone openid email"},
)


@app.route("/")
def index():
    user = session.get("user")
    if user:
        return f'Hello, {user["email"]}. <a href="/logout">Logout</a>'
    else:
        return f'Welcome! Please <a href="/login">Login</a>.'


@app.route("/login")
def login():
    # Alternate option to redirect to /authorize
    # redirect_uri = url_for('authorize', _external=True)
    # return oauth.oidc.authorize_redirect(redirect_uri)
    return oauth.oidc.authorize_redirect("https://")


@app.route("/authorize")
def authorize():
    token = oauth.oidc.authorize_access_token()
    user = token["userinfo"]
    session["user"] = user
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
