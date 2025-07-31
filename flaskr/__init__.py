from flask import Flask, render_template

app = Flask(__name__, instance_relative_config= True)
app.secret_key = "secret_key"

def create_app():
    @app.route("/")
    def index():
        return render_template("index.html")
    
    @app.route("/auth")
    def auth():
        return render_template("auth.html")
    
    @app.route("/profile")
    def profile():
        return render_template("profile.html")

    @app.route("/post")
    def post():
        return render_template("post.html")


    return app
        
app = create_app()
