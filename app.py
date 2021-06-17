import os
from uuid import uuid4
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from subprocess import TimeoutExpired
from common.config import cfg as config
from common.docx2pdf import LibreOfficeError, convert_to
from common.errors import RestAPIError, InternalServerErrorError
from common.files import uploads_url, save_to
import pandas as pd
import re
from tika import parser
import PyPDF2 
import numpy as np    


app = Flask(__name__, static_url_path='')


@app.route('/')
def hello():
    return render_template('index.html')
    


@app.route('/upload', methods=['GET','POST'])
def upload_file():
    # print(request.files)
    if request.method=='POST':
        files_=request.files.getlist('files[]')
        
        sources=[]
        results=[]
        for file in files_:
            upload_id = str(uuid4())
            source = save_to(os.path.join(
                config['uploads_dir'], 'source', upload_id), file )
            sources.append(source)

        
        for source in sources:
            try:
                result = convert_to(os.path.join(
                    config['uploads_dir'], 'pdf', upload_id), source, timeout=45)
                results.append(result)


            except LibreOfficeError:
                raise InternalServerErrorError(
                    {'message': 'Error when converting file to PDF ttttt'})
            except TimeoutExpired:
                raise InternalServerErrorError(
                    {'message': 'Timeout when converting file to PDF'})

        information={}
        c=1

        infos=pd.DataFrame()

        phones=[]
        emails=[]
        loc=[]
        
        for i,j in zip(sources,results):
            file1 = open('{}'.format(j),"rb")
            text = parser.from_file('{}'.format(j))
            text=text['content']
            # print(str(text))
            #regex for email and phone number
            em= re.compile(r'(\b[\w.]+@+[\w.]+.+[\w.]\b)')
            ph=re.compile(r'(?<!\d)(?:\+91|91)?\W*0?(?P<mobile>[789]\d{9})(?!\d)')
            email=em.findall(text)
            phone=ph.findall(text)
            # print(email)
            emails.append(email)
            phones.append(phone)
            loc.append(j)
            file1.close() 
            

            information['file{}:[source,result]'.format(c)]=[i,j]

        infos['file-location']=loc
        infos['phone-numbers']=phones
        infos['emails']=emails

        infos.to_csv('./uploads/details.csv')
        x='details.csv'
        
        return render_template('output.html',tables=[infos.to_html(classes='data')], titles=infos.columns.values,value=x)
    # return jsonify({'result': {'source': uploads_url(source), 'pdf': uploads_url(result)}})


@app.route('/return-files/<filename>')
def return_files_tut(filename):
    file_path = 'uploads/'+filename
    return send_file(file_path, as_attachment=True, attachment_filename='')


@app.route('/uploads/<path:path>', methods=['GET'])
def serve_uploads(path):
    return send_from_directory(config['uploads_dir'], path)


@app.errorhandler(500)
def handle_500_error():
    return InternalServerErrorError().to_response()


@app.errorhandler(RestAPIError)
def handle_rest_api_error(error):
    return error.to_response()


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True,debug=True)
