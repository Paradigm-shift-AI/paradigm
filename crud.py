from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, func
from paradigm.Brain import Brain
import os
import models
import copy
import datetime
import names
import random


class BasicInfo():

    def __init__(self, db: Session, user_id: int):
        self.userId = user_id
        self.db = db

    def get_profile_picture(self):
        return self.db.query(models.Student).filter(models.Student.studentID == self.userId).first().__dict__

    def get_active_classes(self):
        self.active_classes = self.db.query(models.CourseStudent, models.Clas).filter(models.CourseStudent.studentID == self.userId).filter(models.Clas.courseID == models.CourseStudent.courseID).filter(models.Clas.active == 1).all()

        responseList = []
        for i in self.active_classes:
            response = {}
            response["class_id"] = i[1].classID
            response["course_name"] = self.db.query(models.Course).filter(models.Course.courseID == i[0].courseID).first().courseName
            response["participants"] = len(self.db.query(models.Enroll).filter(models.Enroll.classID == i[1].classID).all())
            response["isEnrolled"] = len(self.db.query(models.Enroll).filter(models.Enroll.studentID == self.userId).filter(models.Enroll.classID == i[1].classID).all()) != 0
            responseList.append(response)

        return responseList

    def get_history_classes(self):

        self.history_classes = self.db.query(models.Enroll).filter(models.Enroll.studentID == self.userId).all()

        historyResponseList = []
        _taken_Class = []

        kld = []

        for i in self.history_classes:
            _tk_class = self.db.query(models.Clas).filter(models.Clas.classID == i.classID).first()

            if _tk_class.active == 1:
                continue

            _tk_score = self.db.query(models.Score).filter(models.Score.classID == _tk_class.classID).filter(models.Score.studentID == self.userId).first()

            kld.append((i, _tk_score, _tk_class))


        for i in kld:
            hresponse = {}
            hresponse["classID"] = i[2].classID
            hresponse["course_name"] = self.db.query(models.Course).filter(models.Course.courseID == i[2].courseID).first().courseName
            hresponse["date"] = i[2].date
            hresponse["rank"] = i[1].rank
            hresponse["score"] = str(i[1].totalScore) + "/" + str(len(self.db.query(models.Question).filter(models.Question.classID == i[2].classID).all()))

            historyResponseList.append(hresponse)
            if hresponse["classID"] not in _taken_Class:

                _taken_Class.append(hresponse["classID"])

        return historyResponseList

    def get_response_basic(self):

        resp = {}
        resp["profile"] = self.get_profile_picture()
        resp["history"] = self.get_history_classes()
        resp["active"] = self.get_active_classes()
        resp["profile"].pop('_sa_instance_state', None)

        return resp


class TestReview():

    def __init__(self, session, classID, studentID):
        self.db = session
        self.classID = classID
        self.userId = studentID

    def get_test_review(self):

        questionList = []
        for i in self.db.query(models.Question).filter(models.Question.classID == self.classID).all():
            resp = i.__dict__
            resp.pop("_sa_instance_state", None)
            resp["response"] = self.db.query(models.Response).filter(models.Response.questionID == i.questionID).filter(models.Response.studentID == self.userId).first().valid

            questionList.append(resp)

        respList = {}

        clasObj = self.db.query(models.Clas).filter(models.Clas.classID == self.classID).first()
        respList["date"] = str(clasObj.date)
        respList["course_name"] = self.db.query(models.Course).filter(models.Course.courseID == clasObj.courseID).first().courseName
        scoreObj = self.db.query(models.Score).filter(models.Score.classID == self.classID).filter(models.Score.studentID == self.userId).first()
        respList["score"] = scoreObj.totalScore
        respList["rank"] = scoreObj.rank
        respList["questionList"] = questionList

        return respList

class QuestionTest():

    def __init__(self, session, classID, studentID):
        self.db = session
        self.classID = classID
        self.studentID = studentID

    def get_question_unasked(self):

        ques = self.db.query(models.Question).filter(models.Question.classID == self.classID).all()
        asl = self.db.query(models.QuestionAsked).filter(models.QuestionAsked.studentID == self.studentID).all()


        _ask = []
        for i in asl:
            _ask.append(i.questionID)


        self.respObj = {"question": []}

        for i in ques:
            if i.questionID not in _ask:
                resptemp = copy.deepcopy(i.__dict__)
                resptemp.pop('_sa_instance_state', None)
                self.respObj["question"].append(resptemp)

                id = "{0}_{1}".format(i.questionID, self.studentID)
                self.db.add(models.QuestionAsked(questionAsked=id, studentID=self.studentID, questionID=i.questionID))
                self.db.commit()

        return self.respObj

def get_course_teacher(session, email):
    course = session.query(models.CourseTeacher, models.Teacher).filter(models.Teacher.teacherEmail == email).filter(models.CourseTeacher.teacherID == models.Teacher.teacherID).all()

    resp = []
    for i in course:
        resp.append(session.query(models.Course).filter(models.Course.courseID == i[0].courseID).first().courseName)

    return {"course": set(resp)}

def enroll_in_demo(session, studentID):
    gh = str(studentID) + "_5"
    obj = models.CourseStudent(course_studentID=gh, studentID=studentID, courseID=5)
    session.add(obj)
    session.commit()

def create_class_in_db(session, email, course):
    teacherID = session.query(models.Teacher).filter(models.Teacher.teacherEmail == email).first().teacherID
    course = session.query(models.Course).filter(models.Course.courseName == course).first().courseID
    now = datetime.datetime.now()
    date = now.strftime("%Y-%m-%d")
    _fmin = now.strftime("%m")
    fmin = str(int(_fmin) - int(_fmin)%5)
    time = now.strftime("%Y-%m-%dT%H:"+fmin+":00")

    obj = models.Clas(courseID=course, teacherID=teacherID, date=date, time=time, duration=3600, active=1)
    session.add(obj)
    session.commit()

    session.refresh(obj)
    return obj.classID

def submit_response(session, studentID, questionID, response):
    vale = 0
    if response:
        vale = 1
    obj = models.Response(studentID=studentID, questionID=questionID, valid=vale)
    session.add(obj)
    session.commit()

    return {"message": "Submitted"}

def stop_class(session, classID):
    clas =  session.query(models.Clas).filter(models.Clas.classID == classID).first()
    clas.active = 0

    students = session.query(models.Enroll.studentID).filter(models.Enroll.classID == classID).all()
    _q = session.query(models.Question.questionID).filter(models.Question.classID == classID).all()

    ques = []
    for i in _q:
        ques.append(i[0])

    rest = {}
    srf = {}

    for i in students:
        _sc = session.query(models.Response).filter(models.Response.valid == 1).filter(models.Response.studentID == i[0]).all()
        scr = 0
        for j in _sc:
            if j.questionID in ques:
                scr += 1
        rest[i[0]] = scr
        srf[i[0]] = scr

    rest = [k for k, v in sorted(rest.items(), reverse=True, key=lambda item: item[1])]

    ran = 1
    for i in rest:
        obj = models.Score(classID=classID, studentID=i, totalScore=srf[i], rank=ran)
        ran += 1
        session.add(obj)

    session.commit()

def enroll_class_in_db(session, studntID, classID):
    session.add(models.Enroll(classID=classID, studentID=studntID))
    session.commit()
    return {"message": "Enrolled"}

def get_teacher_info(session, teacherID):
    teacherinfo = session.query(models.Teacher).filter(models.Teacher.teacherID == teacherID).first()
    resp = {}
    resp["name"] = teacherinfo.teacherName
    resp["profilePicture"] = teacherinfo.profilePicture
    resp["course"] = get_course_teacher(session, teacherinfo.teacherEmail)["course"]

def get__list_class_info_teacherDashboard(session, crouseName, teacherID):
    crouseID = session.query(models.Course).filter(models.Course.courseName == courseName).first().courseID

    listOfClass = session.query(models.Clas).filter(models.Clas.crouseID == crouseID).filter(models.Clas.teacherID == teacherID).order_by(models.Clas.date.desc).all()
    respList = []
    for _clas in listOfClass:
        respObj = {}
        respObj["classID"] = _clas.classID
        respObj["className"] = _clas.className
        respObj["date"] = _clas.date
        respObj["questionAsked"] = session.query(func.count(models.Question.questionID)).filter(models.Question.classID == _clas.classID).scalar()
        respObj["flaggedQuestion"] = session.query(func.count(models.Question.questionID)).filter(models.Question.classID == _clas.classID).filter(models.Question.questionFlagged == 1).scalar()
        respObj["attendees"] = session.query(func.courseName(models.Enroll.enrollID)).filter(models.Enroll.classID == _clas.classID).scalar()
        respList.append(respObj)

def get_class_info_for_teacher(session, classID):

    listOfQuestion = session.query(models.Question).filter(models.Question.classID == classID).all()

    graphList = []
    inde = 1
    for question in listOfQuestion:
        graphList.append([str(i), session.query(func.count(models.Response)).filter(models.Response.questionID == question.questionID).filter(models.Response.valid == 1).scalar()])
        inde += 1
        respObj = {}
        respObj["question"] = question.questionText
        respObj["answer"] = question.answer

def create_student(studentID, session):
    obj = models.Student(studentID=studentID, name=str(names.get_full_name()), gender="Male", age=20)
    session.add(obj)
    session.commit()

def qread(a):
    with open("res_text"+a+".txt", "r") as f:
        fg = f.read()
        fg = fg.replace("\n", " ")
    return fg

def inset_question(classID, question, session):
    jk = []

    if question["type"] == 1:
        obj1 = models.Question(questionTypeID=1, classID=classID, text=str(question["question"]), option1=str(question["option1"]), option2=str(question["option2"]), option3=str(question["option3"]), option4=str(question["option4"]), answer=str(question["answer"]), score=question["score"])
        jk.append(obj1)

    if question["type"] == 2:
        obj2 = models.Question(questionTypeID=2, classID=classID, text=str(question["question"]), answer=str(question["answer"]), score=question["score"])
        jk.append(obj2)

    elif question["type"] == 3:
        obj3 = models.Question(questionTypeID=3, classID=classID, text=str(question["question"]), option1=str(question["option1"]), option2=str(question["option2"]), option3=str(question["option3"]), option4=str(question["option4"]), answer1=str(question["answer1"]), answer2=str(question["answer2"]), score=question["score"])
        jk.append(obj3)

    elif question["type"] == 4:
        obj4 = models.Question(questionTypeID=4, classID=classID, text=str(question["question"]), answer=str(question["answer"]), score=str(question["score"]))
        jk.append(obj4)

    session.add(jk[0])
    session.commit()

def generate_question_set(classID, session, set1):
    pg1 = []
    if set1 == 1:
        pg = Brain(qread(""), token_url = "https://fastapiapp.azurewebsites.net/", token_id = "stack-plugin")
        pg1 = pg.generate_question()
    else:
        pg = Brain(qread("0"), token_url = "https://fastapiapp.azurewebsites.net/", token_id = "stack-plugin")
        pg1 = pg.generate_question()

    for question in pg1:
        inset_question(classID, question, session)


if __name__ == '__main__':
    engine = create_engine('mysql+pymysql://vedangj:password@localhost/paradigm')
    Session = sessionmaker(bind=engine)
    session = Session()
    generate_question_set(5, session, 1)
