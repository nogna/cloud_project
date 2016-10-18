from __future__ import absolute_import
from os import path, environ
import json
from flask import Flask, Blueprint, render_template, abort, jsonify, request, session, redirect, url_for, Response
import settings
from mastersendwork import send_task
from start_x_slavevms_MASTERVM import start
from generate_mesh_convert_xml_MASTERVM import generate_convert
from celery import Celery
import sys
import time
import subprocess

app = Flask(__name__)
app.config.from_object(settings)
tasks = []
numdone = 0

def checkifanymore():
    numdonenow = 0
    if tasks!=None:
        for task in tasks:
            if task.ready()==True:
                numdonenow = numdonenow + 1
    if numdone<numdonenow:
        numdone = numdonenow
        return True
    else:
        return False

def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery

celery = make_celery(app)

@celery.task(name="tasks.add")
def add(x, y):
    return x + y

@app.route("/calcajax")
def calc():
    def generate():
        x = 0
        while x < 100:
            print x
            x = x + 10
            time.sleep(0.4)
            yield "data:" + str(x) + "\n\n"
    return Response(generate(), mimetype="text/event-stream")

@app.route("/task_ajax")
def taskajax():
    def generate():
        x = 0
	print(numdone)
        yield "data:" + str(x) + "\n\n"
        while numdone<len(tasks):
            time.sleep(0.1)
            if checkifanymore()==True:
                x = int(numdone/len(tasks))
                yield "data:" + str(x) + "\n\n"
#    if numdone<len(tasks):            
    return Response(generate(), mimetype="text/event-stream")    
#    else:
#        return redirect('/result')    

@app.route("/home")
def home():
    return render_template('index.html')

@app.route("/calculating", methods=['post'])
def calculating():
    if request.method == 'POST':
        numvms = 1
        start_angle = request.form['start_angle']
        stop_angle = request.form['stop_angle']
        num_angles = request.form['n_angles']
        num_levels = request.form['n_levels']
        num_nodes = request.form['n_nodes']
	start(numvms)	
        xml_files = generate_convert()#subprocess.Popen(['python','/home/ubuntu/cloud_project/generate_mesh_convert_xml_MASTERVM.py'])
        print "PROC2: ", xml_files 
        tasks = send_task(xml_files)
	print "LENGTH OF TASK: " + str(len(tasks))
	print tasks
    return render_template('calc.html', start_angle=start_angle, stop_angle=stop_angle)


@app.route("/result")
def result():
    angles=[0,1,2]
    lift_forces=[5,8,9]
    optimal_angle=2
    lift_at_optimal_angle=3
    return render_template('result.html', lift_forces=lift_forces, angles=angles, optimal_angle=optimal_angle, lift_at_optimal_angle=lift_at_optimal_angle)
                      
@app.route("/test/result/<task_id>")
def show_result(task_id):
    retval = add.AsyncResult(task_id).get()
    return repr(retval)

if __name__ == "__main__":
    port = int(environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
