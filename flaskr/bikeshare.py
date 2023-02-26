from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app
)
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename

from flaskr.auth import login_required
from flaskr.db import get_db
import os

bp = Blueprint('bikeshare', __name__)
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

@bp.route('/')
def index():
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, body, created, author_id, username, image'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    return render_template('bikeshare/index.html', posts=posts)

@bp.route('/myposts')
def my_posts():
    db = get_db()
    posts = db.execute(
        'SELECT p.id, title, body, created, author_id, username, image'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE author_id = ?'
        ' ORDER BY created DESC',
        (g.user['id'],)
    ).fetchall()
    return render_template('bikeshare/myposts.html', posts=posts)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        make = request.form['make']
        model = request.form['model']
        year = request.form['year']
        bike_type = request.form['type']
        error = None
        # check if the post request has the file part
        print(request.files)
        if 'image' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['image']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # with current_app.app_context:
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(full_path)
        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            post_id = db.execute(
                'INSERT INTO post (title, body, author_id, image)'
                ' VALUES (?, ?, ?, ?) RETURNING post.id',
                (title, body, g.user['id'], filename)
            ).fetchone()
            print(post_id['id'])
            db.execute(
                'INSERT INTO bike (post_id, owner_id, make, model, year, type)'
                ' VALUES (?, ?, ?, ?, ?, ?)', (int(post_id['id']), g.user['id'], make, model, year, bike_type)
            )
            db.commit()
            return redirect(url_for('bikeshare.index'))

    return render_template('bikeshare/create.html')

def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post

@bp.route('/<int:id>/view', methods=["GET"])
def view(id):
    post = get_db().execute(
        'SELECT post.id, post.title, post.body, post.created, post.author_id, user.username,'
        ' post.image, bike.make, bike.model, bike.type, bike.year'
        ' FROM post'
        ' JOIN user ON user.id = post.author_id'
        ' JOIN bike on bike.post_id = post.id'
        ' WHERE post.id = ?',
        (id,)
    ).fetchone()
    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    return render_template('bikeshare/post.html', post=post)

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if 'image' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['image']
        sql = """UPDATE post SET title = ?, body = ?, img = ?
                WHERE id = ? """
        if file.filename == '':
            sql = """
                UPDATE post SET title = ?, body = ?
                WHERE id = ?
            """
            db = get_db()
            db.execute(
                sql,
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('bikeshare.index'))
            # flash('No selected file')
            # return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # with current_app.app_context:
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(full_path)

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                sql,
                (title, body, filename, id)
            )
            db.commit()
            return redirect(url_for('bikeshare.index'))

    return render_template('bikeshare/update.html', post=post)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('bikeshare.index'))

