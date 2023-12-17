import re
import secrets
from io import BytesIO

from reportlab.lib.colors import black, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from flask import Flask, render_template, session, request, redirect, url_for, jsonify, Response
from models.db_instance import db
from datetime import datetime
import json
from models.type import Type
from models.note import Note
from models.supervisor import Supervisor
from models.topic import Topic
from models.selection import Selection
from models.deadline import Deadline
from models.student import Student

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

'''Set up database'''
HOST = '127.0.0.1'
PORT = '3306'
DATABASE = 'demo'
USERNAME = 'root'
PASSWORD = '20020316'
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}'
db.init_app(app)


def create_tables():
    db.create_all()


'''Set up datetime'''
now = datetime.now()


@app.route('/')
def homepage():
    num_of_topics = Topic.get_num()
    num_of_supervisors = Supervisor.get_num()
    return render_template('home.html', num_of_topics=num_of_topics, num_of_supervisors=num_of_supervisors)


# Click 'My Pickr' button
@app.route('/my_pickr')
def my_pickr():
    if 'user_name' and 'user_type' in session:
        if session['user_type'] == 'student':
            return redirect(url_for('student'))
        elif session['user_type'] == 'supervisor':
            return redirect(url_for('supervisor'))
    else:
        return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_name = request.form.get('user_name')
        password = request.form.get('password')

        student = Student.query.filter_by(user_name=user_name).first()
        supervisor = Supervisor.query.filter_by(user_name=user_name).first()

        if student:
            if student.password == password:
                session['user_name'] = student.english_name
                session['user_type'] = 'student'
                return redirect(url_for('student'))
            else:
                return render_template('login.html', message='Wrong password')

        elif supervisor:
            if supervisor.password == password:
                if supervisor.if_admin == 1:
                    session['user_name'] = supervisor.user_name
                    session['user_type'] = 'admin'
                    return render_template('admin.html')
                else:
                    session['user_name'] = supervisor.user_name
                    session['user_type'] = 'supervisor'
                    return redirect(url_for('supervisor'))
            else:
                return render_template('login.html', message='Wrong password')

        else:
            return render_template('login.html', message='User does not exist')

    else:
        return render_template('login.html', message='Please login')


@app.route('/logout')
def logout():
    session.pop('user_name', None)
    session.pop('user_type', None)
    return redirect(url_for('homepage'))


@app.route('/student')
def student():
    if 'user_name' and 'user_type' in session:
        student_id = Student.get_id(english_name=session['user_name'])
        selection = Selection.get_by_student_id(student_id=student_id)
        supervisors = Supervisor.get_all()
        types = Type.get_all()
        return render_template('student.html', name=session['user_name'], selection=selection, supervisors=supervisors,
                               types=types)
    else:
        return render_template('login.html')


@app.route('/supervisor')
def supervisor():
    if 'user_name' and 'user_type' in session:
        supervisor_id = Supervisor.get_id(user_name=session['user_name'])
        supervisor = Supervisor.get_by_id(id=supervisor_id)
        topics = Topic.get_by_supervisor_id(supervisor_id=supervisor_id)

        total_quta = 0
        for topic in topics:
            total_quta += topic.quota

        return render_template('supervisor.html', topics=topics, supervisor=supervisor, total_quta=total_quta)
    else:
        return render_template('login.html')


@app.route('/delete_topic/<int:topic_id>')
def delete_topic(topic_id):
    topic = Topic.get_by_id(id=topic_id)
    if topic:
        topic.delete()
        return jsonify(success=True)
    else:
        return jsonify(success=False), 404


@app.route('/new_topic')
def new_topic():
    types = Type.get_all()
    return render_template('new_topic.html', types=types)


@app.route('/add_topic', methods=['POST'])
def add_topic():
    supervisor_id = Supervisor.get_id(user_name=session['user_name'])
    topic_name = request.form.get('topic_name')
    type_id = request.form.get('type')
    position = request.form.get('position')
    description = request.form.get('description')
    required_skills = request.form.get('required_skills')
    reference = request.form.get('reference')

    supervisor = Supervisor.get_by_id(id=supervisor_id)
    topics = Topic.get_by_supervisor_id(supervisor_id=supervisor_id)
    types = Type.get_all()

    total_quta = 0
    for topic_in in topics:
        total_quta += topic_in.quota

    if total_quta + int(position) > supervisor.position:
        return render_template('new_topic.html',
                               message='Excess quota, you only have ' + str(supervisor.position) + ' positions.',
                               types=types, topic_name=topic_name, type_id=type_id, position=position,
                               description=description,
                               required_skills=required_skills, reference=reference)

    new_topic = Topic(quota=position, is_custom=False, required_skills=required_skills, reference=reference,
                      name=topic_name,
                      supervisor_id=supervisor_id,
                      description=description, type_id=type_id)
    new_topic.add()
    return redirect(url_for('supervisor'))


@app.route('/edit_topic/<int:topic_id>')
def edit_topic(topic_id):
    topic = Topic.get_by_id(id=topic_id)
    types = Type.get_all()
    return render_template('edit_topic.html', topic=topic, types=types)


@app.route('/update_topic/<int:topic_id>', methods=['POST'])
def update_topic(topic_id):
    topic = Topic.get_by_id(id=topic_id)
    print(topic_id)
    topic_name = request.form.get('topic_name')
    type_id = request.form.get('type')
    position = request.form.get('position')
    description = request.form.get('description')
    required_skills = request.form.get('required_skills')
    reference = request.form.get('reference')

    supervisor_id = Supervisor.get_id(user_name=session['user_name'])
    supervisor = Supervisor.get_by_id(id=supervisor_id)
    topics = Topic.get_by_supervisor_id(supervisor_id=supervisor_id)
    types = Type.get_all()

    total_quta = 0
    for topic_in in topics:
        total_quta += topic_in.quota

    if total_quta + int(position) - topic.quota > supervisor.position:
        return render_template('edit_topic.html',
                               message='Can not save your modify, excess quota, you only have ' + str(
                                   supervisor.position) + ' positions.',
                               topic=topic, types=types)

    topic.update(name=topic_name, supervisor_id=topic.supervisor_id, quota=position, is_custom=False, type_id=type_id,
                 description=description, required_skills=required_skills, reference=reference)
    print('find')
    return redirect(url_for('supervisor'))


# 生成对应老师的选题列表的pdf
@app.route('/topic_poster')
def topic_poster():
    supervisor_id = Supervisor.get_id(user_name=session['user_name'])
    topics = Topic.get_by_supervisor_id(supervisor_id=supervisor_id)
    supervisor = Supervisor.get_by_id(id=supervisor_id)
    print('find')
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=A4, bottomup=0)
    c.setFillColor(black)
    c.rect(0, 0, 595, 842, fill=1)

    max_lines = 4
    line_length = 500
    start_y = 280  # 起始 Y 坐标
    line_spacing = 20  # 行间距
    seed = 220

    # Fonts
    pdfmetrics.registerFont(TTFont('DankMono_Italic', 'static/font/Dank-Mono-Italic.ttf'))
    pdfmetrics.registerFont(TTFont('DankMono', 'static/font/Dank-Mono-Regular.ttf'))

    c.setFont("DankMono_Italic", 40)
    c.setFillColorRGB(225 / 255.0, 108 / 255.0, 99 / 255.0)
    c.drawString(50, 100, supervisor.first_name + '\'s Topics')

    c.setLineWidth(1)
    c.setStrokeColorRGB(225 / 255.0, 108 / 255.0, 99 / 255.0)
    c.line(50, 150, 545, 150)

    for i in range(len(topics)):
        if i < 3:
            c.setFont("DankMono", 20)
            c.setFillColorRGB(225 / 255.0, 108 / 255.0, 99 / 255.0)
            c.drawString(50, 190 + i * seed, topics[i].name)

            c.setFont("DankMono", 15)
            c.setFillColor(white)
            c.drawString(50, 220 + i * seed, topics[i].get_type_name())
            c.drawString(50, 250 + i * seed, str(topics[i].quota) + ' Positions')

            c.setFont("DankMono_Italic", 15)
            c.setFillColorRGB(225 / 255.0, 108 / 255.0, 99 / 255.0)
            c.drawString(200, 250 + i * seed, 'PK' + str(format(topics[i].id, '04d')))

            c.setFillColor(white)
            c.setFont("DankMono", 12)
            for i in range(len(topics)):
                description = topics[i].description
                words = description.split()
                current_line = ""
                line_count = 0

                for word in words:
                    # 测试加入下一个单词后的行长度
                    test_line = (current_line + " " + word if current_line else word)
                    if line_count == max_lines - 1:  # 检查是否为最后一行
                        test_line += "..."  # 假设这一行是最后一行，加上省略号

                    if c.stringWidth(test_line, "DankMono", 12) <= line_length:
                        current_line = test_line
                        if line_count == max_lines - 1:  # 如果是最后一行，直接跳出循环
                            break
                    else:
                        if line_count < max_lines:
                            c.drawString(50, start_y + i * seed + line_count * line_spacing, current_line)
                            line_count += 1
                            current_line = word
                        else:
                            # 如果已经是最后一行，添加省略号并跳出循环
                            current_line += "..."
                            c.drawString(50, start_y + i * seed + line_count * line_spacing, current_line)
                            break

                # 绘制最后一行（如果还有剩余空间且未达到最大行数）
                if line_count < max_lines:
                    c.drawString(50, start_y + i * seed + line_count * line_spacing, current_line)

                c.setLineWidth(1)
                c.setStrokeColorRGB(225 / 255.0, 108 / 255.0, 99 / 255.0)
                c.line(50, 370 + i * seed, 545, 370 + i * seed)

        else:
            if (i-3) % 4 == 0:
                page_index = (i-3) // 4
                c.showPage()
                c.setFillColor(black)
                c.rect(0, 0, 595, 842, fill=1)

                c.setFont("DankMono", 20)
                c.setFillColorRGB(225 / 255.0, 108 / 255.0, 99 / 255.0)
                c.drawString(50, 190 + page_index * seed, topics[i].name)

                c.setFont("DankMono", 15)
                c.setFillColor(white)
                c.drawString(50, 220 + page_index * seed, topics[i].get_type_name())
                c.drawString(50, 250 + page_index * seed, str(topics[i].quota) + ' Positions')

                c.setFont("DankMono_Italic", 15)
                c.setFillColorRGB(225 / 255.0, 108 / 255.0, 99 / 255.0)
                c.drawString(200, 250 + page_index * seed, 'PK' + str(format(topics[i].id, '04d')))

                c.setFillColor(white)
                c.setFont("DankMono", 12)
                for i in range(len(topics)):
                    description = topics[i].description
                    words = description.split()
                    current_line = ""
                    line_count = 0

                    for word in words:
                        # 测试加入下一个单词后的行长度
                        test_line = (current_line + " " + word if current_line else word)
                        if line_count == max_lines - 1:  # 检查是否为最后一行
                            test_line += "..."  # 假设这一行是最后一行，加上省略号

                        if c.stringWidth(test_line, "DankMono", 12) <= line_length:
                            current_line = test_line
                            if line_count == max_lines - 1:  # 如果是最后一行，直接跳出循环
                                break
                        else:
                            if line_count < max_lines:
                                c.drawString(50, start_y + page_index * seed + line_count * line_spacing, current_line)
                                line_count += 1
                                current_line = word
                            else:
                                # 如果已经是最后一行，添加省略号并跳出循环
                                current_line += "..."
                                c.drawString(50, start_y + page_index * seed + line_count * line_spacing, current_line)
                                break

                    # 绘制最后一行（如果还有剩余空间且未达到最大行数）
                    if line_count < max_lines:
                        c.drawString(50, start_y + page_index * seed + line_count * line_spacing, current_line)

                    c.setLineWidth(1)
                    c.setStrokeColorRGB(225 / 255.0, 108 / 255.0, 99 / 255.0)
                    c.line(50, 370 + page_index * seed, 545, 370 + page_index * seed)

    c.save()

    pdf_buffer.seek(0)
    return Response(pdf_buffer, headers={
        'Content-Disposition': 'attachment;filename=topic_poster.pdf',
        'Content-Type': 'application/pdf'
    })


@app.route('/update_selection', methods=['POST'])
def update_selection():
    student_id = Student.get_id(english_name=session['user_name'])
    topic_id = request.form.get('topic_id')
    choice_number = int(request.form.get('choice_number'))
    reset = request.form.get('reset') == 'true'

    selection = Selection.get_by_student_id(student_id=student_id)
    if not selection:
        selection = Selection(student_id=student_id)
        selection.add()

    if reset:
        if choice_number == 1:
            selection.first_topic_id = None
        elif choice_number == 2:
            selection.second_topic_id = None
        elif choice_number == 3:
            selection.third_topic_id = None

        db.session.commit()
        return json.dumps({'success': True, 'reset': True})

    match = re.search(r'\d+', topic_id)
    formatted_topic_id = int(match.group())

    if formatted_topic_id in [selection.first_topic_id, selection.second_topic_id, selection.third_topic_id]:
        return json.dumps({'success': False, 'error': 'You have already selected this topic'})

    topic = Topic.get_by_id(id=formatted_topic_id)

    if topic:
        if match:
            if choice_number == 1:
                selection.first_topic_id = formatted_topic_id
            elif choice_number == 2:
                selection.second_topic_id = formatted_topic_id
            elif choice_number == 3:
                selection.third_topic_id = formatted_topic_id

        db.session.commit()
        return json.dumps({'success': True, 'topic_name': topic.name})
    else:
        return json.dumps({'success': False, 'error': 'Topic does not exist'})


@app.route('/update_custom_topic', methods=['POST'])
def update_custom_topic():
    student_id = Student.get_id(english_name=session['user_name'])
    topic_name = request.form.get('topic_name')
    supervisor_id = request.form.get('supervisor_id')
    description = request.form.get('description')
    type_id = request.form.get('type_id')
    reset = request.form.get('reset') == 'true'

    selection = Selection.get_by_student_id(student_id=student_id)
    if not selection:
        selection = Selection(student_id=student_id)
        selection.add()

    if reset:
        _id = selection.first_topic_id
        selection.first_topic_id = None
        Topic.get_by_id(id=_id).delete()
        db.session.commit()
        return json.dumps({'success': True, 'reset': True})

    new_topic = Topic(quota=1, is_custom=True, required_skills='Null', reference='Null', name=topic_name,
                      supervisor_id=supervisor_id,
                      description=description, type_id=type_id)
    new_topic_id = new_topic.add()

    selection.first_topic_id = new_topic_id
    selection.second_topic_id = None
    selection.third_topic_id = None

    db.session.commit()
    return json.dumps({'success': True, 'topic_name': topic_name})


@app.route('/tutorial')
def tutorial():
    deadlines = Deadline.get_all()
    num = Deadline.get_num()
    notes = Note.get_all()
    return render_template('tutorial.html', deadlines=deadlines, notes=notes, num=num, year=now.year)


@app.route('/topic_list')
def topic_list():
    topics = Topic.get_all()
    types = Type.get_all()
    supervisors = Supervisor.get_all()
    return render_template('topic_list.html', topics=topics, types=types, supervisors=supervisors)


@app.route('/topic_filter')
def topic_filter():
    type_id = request.args.get('type_id')
    supervisor_id = request.args.get('supervisor_id')
    search_query = request.args.get('search_query')

    topics = Topic

    if search_query:
        topics = topics.get_by_name_or_id(search_query=search_query)
    elif supervisor_id:
        topics = topics.get_by_supervisor_id(supervisor_id=supervisor_id)
    elif type_id:
        topics = topics.get_by_type_id(type_id=type_id)

    if topics:
        return json.dumps({'topic_ids': [topic.id for topic in topics]})
    else:
        return json.dumps({'topic_ids': []})


@app.route('/topic_detail/<int:topic_id>')
def topic_detail(topic_id):
    topic = Topic.get_by_id(id=topic_id)
    return render_template('topic_detail.html', topic=topic)


@app.route('/add_student')
def add_student():
    new_student = Student(
        chinese_name='王小明',
        english_name='Wang Xiaoming',
        email="202018020317@qq.com",
        password="123456"
    )
    db.session.add(new_student)
    db.session.commit()
    return "Add student successfully!"


@app.route('/get_student')
def get_student():
    student = Student.query.filter_by(id=1).first()
    return student.chinese_name


@app.route('/add_deadline')
def add_deadline():
    new_deadline = Deadline(
        round_num=1,
        submit_time='2021-01-01 00:00:00',
        result_time='2021-01-02 00:00:00',
        note='第一轮选题'
    )
    new_deadline.add()
    return "Add deadline successfully!"


if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
