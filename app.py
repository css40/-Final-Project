
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_socketio import SocketIO, send
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os 

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///C:/Users/merce/Desktop/blog_flask/blog.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SECRET_KEY'] = 'tu_clave_secreta'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov'}  # Extensiones permitidas

db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Configura Flask-Migrate
socketio = SocketIO(app)
users = {
    'user1': {'name': 'Nombre de usuario', 'bio': 'Biografía del usuario'}
}
# Configura flask-login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)  # Considera cambiar esto a `username` si es más adecuado
    password = db.Column(db.String(100), nullable=False)
    reactions = db.relationship('Reaction', back_populates='user')
    # Relación con el modelo Post
    posts = db.relationship('Post', back_populates='user')

class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    texto = db.Column(db.String, nullable=False)
    imagen_url = db.Column(db.String, nullable=True)  # Nueva columna para la URL de la imagen
    video_url = db.Column(db.String, nullable=True)  # Nueva columna para la URL del video
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reactions = db.relationship('Reaction', back_populates='post')
    user = db.relationship('User', back_populates='posts')


class Reaction(db.Model):
    __tablename__ = 'reactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)  # Usa un tamaño adecuado para los emoticonos

    user = db.relationship('User', back_populates='reactions')
    post = db.relationship('Post', back_populates='reactions')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'post_id', name='unique_user_post_reaction'),
    )
    
@socketio.on('message')
def handle_message(data):
    data['timestamp'] = datetime.utcnow().isoformat()  # Añadir la marca de tiempo
    print(f"Message received: {data}")
    send(data, broadcast=True)

@app.route('/chat-global')
@login_required
def chat_global():
    return render_template('chat.html') 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
@login_required
def inicio():
    posts = Post.query.order_by(Post.fecha.desc()).all()
    return render_template("inicio.html", posts=posts)

@app.route('/profile', methods=['GET'])
@login_required
def profile():
    user = users.get(current_user.id, {'name': 'Nombre de usuario', 'bio': 'Biografía del usuario'})
    return render_template('profile.html', current_user=user)

@app.route('/profile')
def view_profile():
    # código para mostrar el perfil del usuario
    return render_template('profile.html')

@app.route('/profile/edit')
def edit_profile():
    # código para editar el perfil del usuario
    return render_template('edit_profile.html')


@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    user = current_user
    user.bio = request.form['profile_bio']
    
    # Aquí guardar los cambios en la base de datos
    db.session.commit()
    
    # Redirige de vuelta a la página de perfil para que se recargue
    return redirect(url_for('profile'))


@app.route("/agregar")
@login_required
def agregar():
    username = "@" + current_user.name  # Añadir el arroba al nombre de usuario
    return render_template("agregar.html", username=username)

@app.route("/crear", methods=["POST"])
@login_required
def crear_post():
    titulo = request.form.get("titulo")
    texto = request.form.get("texto")
    
    # Manejo de archivos
    imagen = request.files.get("imagen")
    video = request.files.get("video")
    
    imagen_url = None
    video_url = None
    
    if imagen and allowed_file(imagen.filename):
        imagen_filename = secure_filename(imagen.filename)
        imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], imagen_filename))
        imagen_url = url_for('static', filename='uploads/' + imagen_filename)

    if video and allowed_file(video.filename):
        video_filename = secure_filename(video.filename)
        video.save(os.path.join(app.config['UPLOAD_FOLDER'], video_filename))
        video_url = url_for('static', filename='uploads/' + video_filename)
    
    post = Post(titulo=titulo, texto=texto, imagen_url=imagen_url, video_url=video_url, user_id=current_user.id)
    db.session.add(post)
    db.session.commit()
    return redirect("/")
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
           
class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    texto = db.Column(db.String, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

    user = db.relationship('User')
    post = db.relationship('Post', back_populates='comments')

# Añadir la relación en el modelo Post
Post.comments = db.relationship('Comment', back_populates='post', cascade="all, delete-orphan")


@app.route("/crear_comentario/<int:post_id>", methods=["POST"])
@login_required
def crear_comentario(post_id):
    texto = request.form.get("texto")
    comment = Comment(texto=texto, post_id=post_id, user_id=current_user.id)
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('inicio'))

@app.route("/borrar_comentario/<int:comment_id>", methods=["POST"])
@login_required
def borrar_comentario(comment_id):
    comment = Comment.query.get(comment_id)
    if comment and comment.user_id == current_user.id:
        db.session.delete(comment)
        db.session.commit()
        return redirect(url_for('inicio'))
    return "No tienes permiso para borrar este comentario", 403


@app.route("/borrar", methods=["POST"])
@login_required
def borrar():
    post_id = request.form.get("post_id")
    # Buscar el post que corresponde al ID y al usuario actual
    post = Post.query.filter_by(id=post_id, user_id=current_user.id).first()
    
    if post:
        # Eliminar las reacciones asociadas al post
        Reaction.query.filter_by(post_id=post_id).delete()
        
        # Eliminar el post
        db.session.delete(post)
        db.session.commit()
        
        return redirect("/")
    else:
        return "No tienes permiso para borrar este post", 403


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form.get("name")  # Usa 'name' en lugar de 'username'
        password = request.form.get("password")
        user = User.query.filter_by(name=name).first()  # Usa 'name' en lugar de 'username'
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('inicio'))
        else:
            return "Login failed: Invalid name or password", 401
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            return "Passwords do not match", 400

        existing_user = User.query.filter_by(name=name).first()
        if existing_user:
            return "User already exists", 400

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(name=name, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route('/logout')
def logout():
    logout_user()  # Esto cierra la sesión del usuario

    return redirect(url_for('login'))  

@app.route("/add_reaction/<int:post_id>", methods=["POST"])
@login_required
def add_reaction(post_id):
    emoji = request.form.get("emoji")
    existing_reaction = Reaction.query.filter_by(user_id=current_user.id, post_id=post_id).first()

    if existing_reaction:
        flash('Ya has reaccionado a este post.', 'warning')
    else:
        reaction = Reaction(user_id=current_user.id, post_id=post_id, emoji=emoji)
        db.session.add(reaction)
        db.session.commit()
        flash('Reacción añadida con éxito.', 'success')

    return redirect(url_for('inicio'))

@app.route("/eliminar_reaccion/<int:post_id>", methods=["POST"])
@login_required
def eliminar_reaccion(post_id):
    reaction = Reaction.query.filter_by(user_id=current_user.id, post_id=post_id).first()
    if reaction:
        db.session.delete(reaction)
        db.session.commit()
        flash('Reacción eliminada con éxito.', 'success')
    
    return redirect(url_for('inicio'))






if __name__ == "__main__":
    app.run(debug=True)
