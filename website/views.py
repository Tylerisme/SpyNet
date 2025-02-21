from flask import Blueprint, render_template, request, redirect,  url_for 
from googleapiclient.discovery import build
import os
import ast
import json
import requests
from flask import session
from flask import jsonify
from flask_login import login_user , current_user 
from .models import User , db
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from string import ascii_lowercase

views = Blueprint('views', __name__)


SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']

REDIRECT_URI = 'http://localhost:8080/oauth2callback'

TOKEN_FILE = 'token.json'


def get_authenticated_service():
    credentials = None

    try:
        credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    except FileNotFoundError:
        print("Coulndt login")

    youtube = build('youtube', 'v3', credentials=credentials)
    return youtube

def convert_duration(duration):
    duration = duration[2:] 
    hours, minutes, seconds = 0, 0, 0

    if 'H' in duration:
        hours = int(duration.split('H')[0])
        duration = duration.split('H')[1]

    if 'M' in duration:
        minutes = int(duration.split('M')[0])
        duration = duration.split('M')[1]

    if 'S' in duration:
        seconds = int(duration.split('S')[0])

    formatted_duration = '{:02d}:{:02d}:{:02d}'.format(hours, minutes, seconds)
    return formatted_duration

def get_playlist_videos(playlist_id):
    youtube = get_authenticated_service()
    discord_log(f"Using youtube api to fetch : <https://www.youtube.com/playlist?list={playlist_id}> <@709799648143081483>")

    # Fetch the playlist items
    playlist_items = []
    next_page_token = None

    while True:
        playlist_request = youtube.playlistItems().list(
            part='snippet',
            playlistId=playlist_id,
            maxResults=50,  # Adjust as needed
            pageToken=next_page_token
        )
        playlist_response = playlist_request.execute()

        playlist_items.extend(playlist_response['items'])
        next_page_token = playlist_response.get('nextPageToken')

        if not next_page_token:
            break

    videos = []

    for index, item in enumerate(playlist_items):
        video_id = item['snippet']['resourceId']['videoId']

        video_request = youtube.videos().list(
            part='contentDetails',
            id=video_id
        )
        video_response = video_request.execute()
        try:
            video_duration = video_response['items'][0]['contentDetails']['duration']
        except IndexError:
            video_duration = "N/a"
        formatted_duration = convert_duration(video_duration)
        video_title = item['snippet']['title']

        videos.append({
            'id': video_id,
            'title': video_title,
            'duration': formatted_duration,
            'jsid': index 
        })

    return videos

#Main function to /update (Youtube file create)
def createtxtfile(name ,playlist_id ):
    videos = get_playlist_videos(playlist_id)
    with open(f"website/playlists/{name}.txt", 'w' , encoding='utf-8') as file:
        file.write(str(videos))
    return videos  

# Send a discord message (Log to #logs)
def discord_log(message):
    messageeeee = { 'content': message }
    payload = json.dumps(messageeeee)
    headers = {'Content-Type': 'application/json'}
    requests.post("https://discord.com/api/webhooks/1212485016903491635/4BZmlRW3o2LHBD2Rji5wZSRAu-LonJZIy-l_SvMaluuCSB_cS1kuoofhtPt2pq2m6AuS", data=payload, headers=headers)


#Uptime robot 
@views.route('/monitor')
def monitor():
      return "Working"



#Login route (whitelist_ips is from EG)

blacklist_ips =  set()  
whitelist_ips =  set()  

@views.route('/login', methods=['GET', 'POST'])
def login():
    client_ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
    user_agent = request.headers.get('User-Agent')
    if current_user.is_authenticated:
        return redirect(url_for('views.home'))
    if client_ip in blacklist_ips :
        return jsonify(message="Error 403"), 403

    if client_ip not in whitelist_ips :
        api_url = f'https://ipinfo.io/{client_ip}?token=8f8d5a48b50694'
        response = requests.get(api_url)
        data = response.json()

        if 'country' in data:
                country_code = data['country']
                if country_code != 'EG':
                    blacklist_ips.add(client_ip)
                    return jsonify(message="Please disable vpn/proxy."), 403
        else:
            blacklist_ips.add(client_ip)
            return jsonify(message="Unable to determine the country. Login failed."), 403
                            
    whitelist_ips.add(client_ip)

    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        if username == "spy":
            return "Login unsuccessful."
        if username == "Amoor2025":
            user = User.query.filter_by(username="spy").first()
            username = "spy"
        if user :
            login_user(user)
            user.active_sessions += 1
            db.session.commit()
            discord_log(f"{client_ip} just logged in with {username} Device ```{user_agent}```  <@709799648143081483>")
            session.permanent = True
            return redirect(url_for('views.home'))

        else:
            discord_log(f"{client_ip} just failed to login with '{username}' Device ```{user_agent}``` <@709799648143081483>")
            return "Login unsuccessful."

    return render_template('used_pages/login.html')


#Login 2 For proxy / outside EG (Doesnt add to the active sessions)

@views.route('/login2', methods=['GET', 'POST'])
def login2():
    client_ip = request.headers['X-Forwarded-For'].split(',')[0].strip()
    user_agent = request.headers.get('User-Agent')

    if current_user.is_authenticated:
        return redirect(url_for('views.home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        if username == "spy":
            return "Login unsuccessful."
        if username == "Amoor2025":
            user = User.query.filter_by(username="spy").first()
            username = "spy"
        if user:
            login_user(user)
            discord_log(f"LOGIN2 {client_ip} just logged in with {username} Device ```{user_agent}```  <@709799648143081483>")
            session.permanent = True
            return redirect(url_for('views.home'))
        else:
            discord_log(f"LOGIN2 {client_ip} just failed to login with '{username}' Device ```{user_agent}``` <@709799648143081483> LOGIN2")
            return "Login unsuccessful."

    return render_template('used_pages/login.html')


#All links works with this
@views.route('/redirect/<path:link>')
def redirectlinks(link):
      link =  link.replace('questionmark', '?')
      link =  link.replace('andsympol', '&')

      return redirect(f"{link}") 

#Home
@views.route("/")
def home():
    # lines = ["physics", "chemistry","maths" , "arabic", "german" , "english" ,"biology", "geology"]
    lines = ["chemistry", "english","maths" , "arabic", "german" , "physics" ,"biology", "geology"]

    return render_template('used_pages/all.html', lines=lines , teachername="All")


#Favicon

@views.route('/favicon.ico')
def favicon():
    return redirect("/static/favicon.ico") 


#accs(accounts) 
@views.route('/spyaccs')
def spyleakedaccs():
    if current_user.username not in ['spy', 'skailler']:
        return redirect(url_for('views.home'))
    else:
        with open('website/templates/spyaccs/accs.json') as json_file:
            accs = json.load(json_file)
        return render_template('spyaccs/index.html' , accs = accs)
  



#Subjects from here ===============================================================================================
#==================================================================================================================

#Physics --------------------------------------------------------------------------------------------------------------------------
@views.route('/physics')
def Physics():
  teacher_links = {
  "Nawar": ("/nawar", "Ahmad Nawar"),
  "Tamer-el-kady": ("/tamer-el-kady", "Tamer el kady"),

  }
  teachername = "Physics"
  return render_template('used_pages/teacher.html',
                         teacher_links=teacher_links,
                         teachername=teachername,
                         imgs="yes")


@views.route('/tamer-el-kady')
def tamerelkady():
  teachername = "Tamer El Kady"
  playlist_id = 'PLM-GVlebsoPXm9cPbwmEllBmG1cY3C5_t'
  folder = "https://drive.google.com/drive/folders/1n1jJte2y40YEuxsq0TiohJGafP3rwj-W?usp=drive_link"
  with open("website/playlists/tamerelkady.txt", 'r', encoding='utf-8') as file:
        content = file.read()
        videos = ast.literal_eval(content)
  return render_template('used_pages/videopage.html',
                         videos=videos,
                         playlist_id=playlist_id,
                         teachername=teachername, folder=folder)    


@views.route("/tamer-el-kadyupdate")
def tamerelkadyupdate():
    return createtxtfile("tamerelkady" , "PLM-GVlebsoPXm9cPbwmEllBmG1cY3C5_t")




#Nawar -------------------------------------------

def load_nawar_info():
    with open('website/Backend/nawar.json', 'r') as file:
        info = json.load(file)
    return info


@views.route('/nawar')
def nawar():
  info = load_nawar_info()

  teacher_links = {
        f"Nawar {course}": (f"/nawar{info[course]['url']}", info[course]['description'])
        for course in info
    }
  teachername = "Physics"
  return render_template('used_pages/teacher.html',
                         teacher_links=teacher_links,
                         teachername=teachername,
                         imgs="yes")

@views.route("/nawar/<custom_url>/update")
def nawarupdate(custom_url):
    info = load_nawar_info()
    course_key = next((name for name, info in info.items() if info['url'] == f"/{custom_url}"), None)
    if course_key not in info:
        return redirect(url_for('views.display_links'))
    playlist_id = info[course_key]["id"]
    return createtxtfile(f"nawar{course_key}", playlist_id)


@views.route("/nawar/<custom_url>")
def nawarvids(custom_url):
    info = load_nawar_info()
    course_info = next((info for info in info.values() if info['url'] == f"/{custom_url}"), None)
    course_name = next((name for name, info in info.items() if info['url'] == f"/{custom_url}"), None)
    teachername = course_name
    playlist_id = course_info["id"]
    with open(f"website/playlists/nawar{course_name}.txt", 'r', encoding='utf-8') as file:
            content = file.read()
            videos = ast.literal_eval(content)

    return render_template('used_pages/videopage.html',
                         videos=videos,
                         playlist_id=playlist_id,
                         teachername=teachername)





#Chemistry --------------------------------------------------------------------------------------------------------------------------
@views.route('/chemistry')
def chem():
  teacher_links = {
     "Zoz": ("nasser", "Nasser-El-Batal"),
     "Ashraf elshnawy": ("ashraf", "All sessions", "New"),
     "Ashraf elshnawy(YT)": ("ashrafelshnawy", "Revision CH 1-4"),

  }
  teachername = "Chemistry"
  return render_template('used_pages/teacher.html',
                         teacher_links=teacher_links,
                         teachername=teachername,
                         imgs="yes")



#Ashraf -----------------------------------------------------------------------------


@views.route('/ashraf')
def ashraf():
    with open('website/Backend/ashraf.json', 'r') as file:
        lectures_data = json.load(file)
        # Extracting the last lecture ID
        last_lecture_id = lectures_data['filtered_lectures'][-1]['title']
    return render_template('used_pages/ashraf.html', lectures_data=lectures_data, last_lecture_id=last_lecture_id)



@views.route('/ashraf/update')
def updateashraf():
    headers = {
        'authority': 'api.csacademyzone.com',
        'accept': 'application/json, text/plain, */*',
    }
    json_data = {
        'active': 1,
    }
    response = requests.post('https://api.csacademyzone.com/lectures', headers=headers, json=json_data)
    data = response.json()
    filtered_lectures = []
    last_id = None

    for lecture in data['lectures']:
        filtered_lecture = {
            "id": lecture["id"],
            "title": lecture["title"]
        }
        for part in ascii_lowercase:
            part_key = f"part_{part}_video"
            if part_key in lecture and lecture[part_key]:
                filtered_lecture[part_key] = lecture[part_key]
        filtered_lectures.append(filtered_lecture)
        last_id = lecture["id"] 

    result = {"filtered_lectures": filtered_lectures}

    with open("website/Backend/ashraf.json", 'w') as output_file:
        json.dump(result, output_file, indent=2)
    
    if response.status_code == 200:
        return f"Done. Last ID: {last_id}" 
    else:
        return "An error occurred!"



@views.route('/ashraf/<video_id>', methods = ['POST'])
def ashrafpost(video_id):
    if request.method == 'POST' :
        try:
            student_name = "spy"
            url = "https://api.csacademyzone.com/video/otp"
            params = {"student_name": student_name, "video_id": video_id}
            headers = {"Content-type": "application/x-www-form-urlencoded", "sessionToken": "imcool"}
            response = requests.post(url, data=params, headers=headers)
            if response.status_code == 401:
                data = response.json()
                otp = data.get("otp")
                playback_info = data.get("playbackInfo")
                return jsonify({"otp": otp, "playbackInfo": playback_info})
            else:
                return jsonify({"error": f"Failed to get OTP. Status code: {response.status_code}"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        




@views.route("/ashrafelshnawy")
def ashrafelshnawy():
  teachername = "Ashraf El Shnawy"
  playlist_id = 'PLM-GVlebsoPW0BYrJMns3WklFGZHzNtmV'
  with open("website/playlists/ashrafelshnawy.txt", 'r', encoding='utf-8') as file:
        content = file.read()
        videos = ast.literal_eval(content)
  return render_template('used_pages/videopage.html',
                         videos=videos,
                         playlist_id=playlist_id,
                         teachername=teachername)




@views.route("/ashrafelshnawyupdate")
def ashrafelshnawyupdate():
    return createtxtfile("ashrafelshnawy" , "PLM-GVlebsoPW0BYrJMns3WklFGZHzNtmV")

# Nasser --------------------------------------------------------------



def load_nasser_info():
    with open('website/Backend/nasser.json', 'r') as file:
        nasser_info = json.load(file)
    return nasser_info


@views.route('/nasser')
def nasser():
  nasser_info = load_nasser_info()

  teacher_links = {
        f"Nasser-El-Batal {course}": (f"/nasser{nasser_info[course]['url']}", nasser_info[course]['description'])
        for course in nasser_info
    }
  teachername = "Chemistry"
  return render_template('used_pages/teacher.html',
                         teacher_links=teacher_links,
                         teachername=teachername,
                         imgs="yes")

@views.route("/nasser/<custom_url>/update")
def nasserupdate(custom_url):
    nasser_info = load_nasser_info()
    course_key = next((name for name, info in nasser_info.items() if info['url'] == f"/{custom_url}"), None)
    if course_key not in nasser_info:
        return redirect(url_for('views.display_links'))
    playlist_id = nasser_info[course_key]["id"]
    return createtxtfile(f"nasser{course_key}", playlist_id)


@views.route("/nasser/<custom_url>")
def nasservids(custom_url):
    nasser_info = load_nasser_info()
    course_info = next((info for info in nasser_info.values() if info['url'] == f"/{custom_url}"), None)
    course_name = next((name for name, info in nasser_info.items() if info['url'] == f"/{custom_url}"), None)
    teachername = course_name
    playlist_id = course_info["id"]
    with open(f"website/playlists/nasser{course_name}.txt", 'r', encoding='utf-8') as file:
            content = file.read()
            videos = ast.literal_eval(content)

        
    teacher_pdf_mapping = {
        "Chapter 1": "https://drive.google.com/drive/folders/1otLcK6atSsKhZGIo7Cz0hRxoZ7gbN8nz?usp=drive_link",
        "Chapter 2": "https://drive.google.com/drive/folders/1yY4NSy-guuvbtSUGuRg6uXh6nxi4XXmY?usp=drive_link",
        "Chapter 3": "https://drive.google.com/drive/folders/1CqVC871-_kgNxNuJtpXAkp8BMHWL0cqU?usp=drive_link",
        "Chapter 4": "https://drive.google.com/drive/folders/1xtEHPFPHAiyXaQ62Ou2MRkklZmBvWzZd?usp=drive_link",
        "Chapter 5": "https://drive.google.com/drive/folders/1zda1ANurONO44MTBIo2tm4wkhGahtUUn?usp=drive_link",


        }
    if course_name in teacher_pdf_mapping:
        folder = teacher_pdf_mapping[teachername]


    return render_template('used_pages/videopage.html',
                         videos=videos,
                         playlist_id=playlist_id,
                         teachername=teachername,
                         folder = folder)





#Math --------------------------------------------------------------------------------------------------------------------------
@views.route('/maths')
def math():
  teacher_links = {
  "Sherbo": ("/sherbo", "Omar sherbeni"),
    "Salama": ("/salama", "Mohamed Salama")
  }
  teachername = "Math"
  return render_template('used_pages/teacher.html',
                         teacher_links=teacher_links,
                         teachername=teachername,
                         imgs="yes")






#Sherbo ------------------------

 
@views.route('/sherbo')
def sherbo():
  sherbo_info = load_sherbo_info()

  teacher_links = {
        course: (f"/sherbo{sherbo_info[course]['url']}", sherbo_info[course]['description'])
        for course in sherbo_info
    }
  teachername = "Math"
  return render_template('used_pages/teacher.html',
                         teacher_links=teacher_links,
                         teachername=teachername,
                         imgs="yes")

def load_sherbo_info():
    with open('website/Backend/sherbo.json', 'r') as file:
        sherbo_info = json.load(file)
    return sherbo_info


@views.route("/sherbo/<custom_url>/update")
def sherboupdates(custom_url):
    sherbo_info = load_sherbo_info()
    course_key = next((name for name, info in sherbo_info.items() if info['url'] == f"/{custom_url}"), None)
    if course_key not in sherbo_info:
        return redirect(url_for('views.display_links'))
    playlist_id = sherbo_info[course_key]["id"]
    return createtxtfile(f"sherbo{course_key}", playlist_id)

@views.route("/sherbo/<custom_url>")
def sherporoutes(custom_url):
    extra = None
    sherbo_info = load_sherbo_info()
    course_info = next((info for info in sherbo_info.values() if info['url'] == f"/{custom_url}"), None)
    course_name = next((name for name, info in sherbo_info.items() if info['url'] == f"/{custom_url}"), None)
    teachername = course_name
    playlist_id = course_info["id"]
    with open(f"website/playlists/sherbo{course_name}.txt", 'r', encoding='utf-8') as file:
            content = file.read()
            videos = ast.literal_eval(content)

    if course_name  == "Dynamics" :
        extra = { 
            "S1.pdf" : "https://drive.google.com/file/d/1pdTVxYtcEqfaWZb3laZeWXJjsrOh36SH/view?usp=drive_link" ,
            "S2.pdf" : "https://drive.google.com/file/d/1EiLz7HXdDspctVpna-8LRaL0w7wFDAC-/view?usp=drive_link" , 
            "S3.pdf" : "https://drive.google.com/file/d/1RA0zMCf9KPUaCf_8BR4XcLGV_43YJKpI/view?usp=drive_link" ,
            "S4.pdf" : "https://drive.google.com/file/d/1s9vH8ddCXxgI5Zq9305NaRA6XmXoB7Xf/view?usp=drive_link", 
            "S5.pdf" : "https://drive.google.com/file/d/1tLCq4hgMcC4NX3cXLkgpn-co0nbFmx4C/view?usp=drive_link",
                   } 
    
        folder = "https://drive.google.com/drive/folders/1SBpcOBHoGSsxnROkQWVmFOuIxuxKhK8S?usp=drive_link"

    elif course_name  == "Calculus":
        folder = "https://drive.google.com/drive/folders/142TCiyG-oCmkpgeLpEnHmGaRSmnN6Och?usp=drive_link" 


    elif course_name  == "Statics" :
        folder =   "https://drive.google.com/drive/folders/192Zd0BMB0-ohwV2dYsSJvFB651d7qXAS?usp=drive_link"  

    return render_template('used_pages/videopage.html', videos=videos, playlist_id=playlist_id, teachername=teachername ,extra = extra , folder =folder)






# Salama --------------------------------------------------------
@views.route('/salama')
def salama():
    salama_info = load_salama_info()

    teacher_links = {
        course: (f"/salama{salama_info[course]['url']}", course)
        for course in salama_info
    }
    teachername = "Math"
    return render_template('used_pages/teacher.html', teacher_links=teacher_links, teachername=teachername, imgs="yes")



def load_salama_info():
    with open('website/Backend/salama.json', 'r') as file:
        salama_info = json.load(file)
    return salama_info


def add_course(course_name, course_id,input3, course_image):
    salama_info = load_salama_info()
    if course_image:
        filename = course_name + '.jpg'
        upload_path = os.path.join('website/static/assets/Math/', filename)
        course_image.save(upload_path)
        new_course = {"id": course_id , "url" : input3}
        salama_info[course_name] = new_course
        with open('website/Backend/salama.json', 'w') as file:
            json.dump(salama_info, file, indent=2)
        return f"Course '{course_name}' added successfully."
    else:
        return "Invalid file format or no file provided."

@views.route("/salama/add-course", methods=['GET', 'POST'])
def salama_add_course_route():
    if current_user.username in ['spy', 'skailler']:
        if request.method == 'POST':       
            
            input1 = request.form.get('input1')
            input2 = request.form.get('input2')  
            input3 = f"/{request.form.get('input3')}"  

            course_image = request.files['course_image']
            return add_course(input1, input2,input3, course_image)

        
    return render_template('backend_pages/add-course.html')
    





@views.route("/salama/edit-course", methods=['GET', 'POST'])
def salama_edit_course_route():
    if current_user.username in ['spy', 'skailler']:
        if request.method == 'POST':
            selected_course = request.form.get('course_select')
            new_course_id = request.form.get('course_id')
            new_course_url = request.form.get('course_url')

            with open('website/Backend/salama.json', 'r') as file:
                your_courses_data = json.load(file)

            if selected_course in your_courses_data:
                your_courses_data[selected_course]['id'] = new_course_id
                your_courses_data[selected_course]['url'] = new_course_url

                with open('website/Backend/salama.json', 'w') as file:
                    json.dump(your_courses_data, file, indent=2)

            uploaded_file = request.files.get('course_image')
            if uploaded_file :
                filename = selected_course + '.jpg'
                upload_path = os.path.join('website/static/assets/Math/', filename)
                uploaded_file.save(upload_path)



            return f"Edited {selected_course} !"
        
        with open('website/Backend/salama.json', 'r') as file:
            courses = json.load(file)

        return render_template('backend_pages/edit-course.html', courses =courses , selectedCourse=None)
    
    return render_template('backend_pages/edit-course.html', courses =courses , selectedCourse=None)










@views.route("/salama/<custom_url>/update")
def salamacoursesupdate(custom_url):
    salama_info = load_salama_info()
    course_key = next((name for name, info in salama_info.items() if info['url'] == f"/{custom_url}"), None)
    if course_key not in salama_info:
        return redirect(url_for('views.display_links'))
    playlist_id = salama_info[course_key]["id"]
    return createtxtfile(f"salama{course_key}", playlist_id)

@views.route("/salama/<custom_url>")
def salamaroutes(custom_url):
    extra = None
    salama_info = load_salama_info()
    course_info = next((info for info in salama_info.values() if info['url'] == f"/{custom_url}"), None)
    course_name = next((name for name, info in salama_info.items() if info['url'] == f"/{custom_url}"), None)
    teachername = course_name
    playlist_id = course_info["id"]
    with open(f"website/playlists/salama{course_name}.txt", 'r', encoding='utf-8') as file:
            content = file.read()
            videos = ast.literal_eval(content)
    if course_name  == "Course 6" :
       extra={"Pdf 1" :"https://drive.google.com/file/d/18mnyKrmeiNNZMBdaJ0sD8VAkAzLbM15r/view?usp=drive_link" , "Pdf 2" : "https://drive.google.com/file/d/1JLwNyWB8lOVSdVi8IvA6zb1D1iVQ8H3l/view?usp=drive_link"}   
    elif course_name  == "Course 17" :
        extra = {"Pdf 1" : "https://drive.google.com/file/d/1Ng8UkfF48_Cj1ZjiMn8NPfkWEONh3vJD/view?usp=drive_link"}
    elif course_name  == "Course 19":
        extra={"Pdf 1" :"https://drive.google.com/file/d/1a-56mRMP3nYSts90itOfINMtmrb8z6rr/view?usp=drive_link" , "Pdf 2" : "https://drive.google.com/file/d/1O21TqOmEJv2R9zUJmMw0BFnHsjCtqEVF/view?usp=drive_link"}   
    return render_template('used_pages/videopage.html', videos=videos, playlist_id=playlist_id, teachername=teachername ,extra = extra)


#Arabic --------------------------------------------------------------------------------------------------------------------------
@views.route('/arabic')
def gedo():
  teacher_links = {
    "Gedo": ("gedoo", "Reda El Farouk"),
    "El kaysaar": ("mohamedtarek", "Mohamed Tarek"),
    "Mohamed salah": ("mohamedsalah", "Mohamed Salah"),


}
  teachername = "Arabic"
  return render_template('used_pages/teacher.html',
                         teacher_links=teacher_links,
                         teachername=teachername,
                         imgs="yes")


@views.route("/mohamedsalah")
def mohamedsalah():
    playlist_id = 'PLM-GVlebsoPXv3dz0yaqJtvjkOAN6KNRc'
    teachername= "Mohamed Salah"
    with open("website/playlists/mohamedsalah.txt", 'r', encoding='utf-8') as file:
        content = file.read()
        videos = ast.literal_eval(content)
    return render_template('used_pages/videopage.html',
                           videos=videos,
                           playlist_id=playlist_id,
                           teachername=teachername)

@views.route("/mohamedsalahupdate")
def mohamedsalahupdate():
    return createtxtfile("mohamedsalah" , "PLM-GVlebsoPXv3dz0yaqJtvjkOAN6KNRc")







@views.route("/mohamedtarek")
def mohamedtarek():
    playlist_id = 'PLM-GVlebsoPWeP1pGCJWmf20Uc2Cu4JWN'
    teachername= "Mohamed Tarek"
    with open("website/playlists/mohamedtarek.txt", 'r', encoding='utf-8') as file:
        content = file.read()
        videos = ast.literal_eval(content)
    return render_template('used_pages/videopage.html',
                           videos=videos,
                           playlist_id=playlist_id,
                           teachername=teachername)


@views.route("/mohamedtarekupdate")
def mohamedtarekupdate():
    return createtxtfile("mohamedtarek" , "PLM-GVlebsoPWeP1pGCJWmf20Uc2Cu4JWN")




@views.route("/gedoo")
def gedoo2():
    playlist_id = 'PLM-GVlebsoPXBcSNcLjkmcQG53hQYTvui'
    teachername= "Gedo"
    with open("website/playlists/gedo.txt", 'r', encoding='utf-8') as file:
        content = file.read()
        videos = ast.literal_eval(content)
    return render_template('used_pages/videopage.html',
                           videos=videos,
                           playlist_id=playlist_id,
                           teachername=teachername)


@views.route("/gedooupdate")
def gedoupdate():
    return createtxtfile("gedo" , "PLM-GVlebsoPXBcSNcLjkmcQG53hQYTvui")




#Geology --------------------------------------------------------------------------------------------------------------------------
@views.route('/geology')
def geology():
  teacher_links = {
    "Sameh": ("sameh", "Sameh Nash2t"),
    "Gio maged": ("giomaged", "Gio maged")
  }
  teachername = "Geology"
  return render_template('used_pages/teacher.html',
                          teacher_links=teacher_links,
                          teachername=teachername,
                          imgs="yes")



def load_sameh_info():
    with open('website/Backend/sameh.json', 'r') as file:
        info = json.load(file)
    return info


@views.route('/sameh')
def sameh():
  info = load_sameh_info()

  teacher_links = {
        f"Sameh Nash2t {course}": (f"/sameh{info[course]['url']}", info[course]['description'])
        for course in info
    }
  teachername = "Geology"
  return render_template('used_pages/teacher.html',
                         teacher_links=teacher_links,
                         teachername=teachername,
                         imgs="yes")

@views.route("/sameh/<custom_url>/update")
def samehupdate(custom_url):
    info = load_sameh_info()
    course_key = next((name for name, info in info.items() if info['url'] == f"/{custom_url}"), None)
    if course_key not in info:
        return redirect(url_for('views.display_links'))
    playlist_id = info[course_key]["id"]
    return createtxtfile(f"sameh{course_key}", playlist_id)


@views.route("/sameh/<custom_url>")
def samehvids(custom_url):
    info = load_sameh_info()
    course_info = next((info for info in info.values() if info['url'] == f"/{custom_url}"), None)
    course_name = next((name for name, info in info.items() if info['url'] == f"/{custom_url}"), None)
    teachername = course_name
    playlist_id = course_info["id"]
    with open(f"website/playlists/sameh{course_name}.txt", 'r', encoding='utf-8') as file:
            content = file.read()
            videos = ast.literal_eval(content)

    return render_template('used_pages/videopage.html',
                         videos=videos,
                         playlist_id=playlist_id,
                         teachername=teachername)





@views.route("/giomaged")
def giomaged():
  teachername = "Gio maged"
  playlist_id = 'PLM-GVlebsoPXh1obVV3aWysV7wXlN3yET'
  with open("website/playlists/giomaged.txt", 'r', encoding='utf-8') as file:
        content = file.read()
        videos = ast.literal_eval(content) 
  return render_template('used_pages/videopage.html',
                         videos=videos,
                         playlist_id=playlist_id,
                         teachername=teachername)



@views.route("/giomagedupdate")
def giomagedupdate():
    return createtxtfile("giomaged" , "PLM-GVlebsoPXh1obVV3aWysV7wXlN3yET")


#Biology----------------------------------------------------------------------------------------------------------------------
@views.route('/biology')
def bio():
  teacher_links = {
     "Daif": ("daif", "Mohamed Daif"),
  }
  teachername = "Biology"
  return render_template('used_pages/teacher.html',
                         teacher_links=teacher_links,
                         teachername=teachername,
                         imgs="yes")


def load_daif_info():
    with open('website/Backend/daif.json', 'r') as file:
        info = json.load(file)
    return info


@views.route('/daif')
def daif():
  info = load_daif_info()

  teacher_links = {
        f"{course}": (f"/daif{info[course]['url']}", info[course]['description'])
        for course in info
    }
  teachername = "Biology"
  return render_template('used_pages/teacher.html',
                         teacher_links=teacher_links,
                         teachername=teachername,
                         imgs="yes")

@views.route("/daif/<custom_url>/update")
def daifupdates(custom_url):
    info = load_daif_info()
    course_key = next((name for name, info in info.items() if info['url'] == f"/{custom_url}"), None)
    if course_key not in info:
        return redirect(url_for('views.display_links'))
    playlist_id = info[course_key]["id"]
    return createtxtfile(f"daif{course_key}", playlist_id)


@views.route("/daif/<custom_url>")
def daifvids(custom_url):
    info = load_daif_info()
    course_info = next((info for info in info.values() if info['url'] == f"/{custom_url}"), None)
    course_name = next((name for name, info in info.items() if info['url'] == f"/{custom_url}"), None)
    teachername = course_name
    playlist_id = course_info["id"]
    with open(f"website/playlists/daif{course_name}.txt", 'r', encoding='utf-8') as file:
            content = file.read()
            videos = ast.literal_eval(content)

    return render_template('used_pages/videopage.html',
                         videos=videos,
                         playlist_id=playlist_id,
                         teachername=teachername)


#-----------------------------------------------------------------------------------------------------------

@views.route('/english')
def english():
  teacher_links = {
     "Hossam Sameh": ("english/hossamsameh", "The leader" , "Neww"),

     "Ahmed Salah": ("english/ahmadsalah", "Ahmed Salah"),


  }
  teachername = "English"
  return render_template('used_pages/teacher.html',
                         teacher_links=teacher_links,
                         teachername=teachername,
                         imgs="yes")


@views.route("/english/ahmadsalah")
def ahmadsalah():
  teachername = "Ahmad Salah"
  playlist_id = 'PLM-GVlebsoPUWOjoc9DyO2Jh8mclaRY1Q'
  with open("website/playlists/ahmadsalah.txt", 'r', encoding='utf-8') as file:
        content = file.read()
        videos = ast.literal_eval(content)
  return render_template('used_pages/videopage.html',
                         videos=videos,
                         playlist_id=playlist_id,
                         teachername=teachername)

@views.route("/english/ahmadsalah/update")
def ahmadsalahupdate():
    return createtxtfile("ahmadsalah" , "PLM-GVlebsoPUWOjoc9DyO2Jh8mclaRY1Q")


@views.route("/english/hossamsameh")
def hossamsameh():
  teachername = "Hossam Sameh"
  playlist_id = 'PLM-GVlebsoPWGSfDq2_C801iLUl3RKWCK'
  with open("website/playlists/hossamsameh.txt", 'r', encoding='utf-8') as file:
        content = file.read()
        videos = ast.literal_eval(content)
  return render_template('used_pages/videopage.html',
                         videos=videos,
                         playlist_id=playlist_id,
                         teachername=teachername)

@views.route("/english/hossamsameh/update")
def hossamsamehupdate():
    return createtxtfile("hossamsameh" , "PLM-GVlebsoPWGSfDq2_C801iLUl3RKWCK")






@views.route('/german')
def german():
  teacher_links = {
     "German": ("germann", "Abd El Moez"),

  }
  teachername = "German"
  return render_template('used_pages/teacher.html',
                         teacher_links=teacher_links,
                         teachername=teachername,
                         imgs="yes")

@views.route("/germann")
def germann():
  teachername = "German"
  playlist_id = 'PLM-GVlebsoPWNh__WI8QAIN2xQjawgB4i'
  with open("website/playlists/germann.txt", 'r', encoding='utf-8') as file:
        content = file.read()
        videos = ast.literal_eval(content)
  return render_template('used_pages/videopage.html',
                         videos=videos,
                         playlist_id=playlist_id,
                         teachername=teachername)

@views.route("/germannupdate")
def germannupdate():
    return createtxtfile("germann" , "PLM-GVlebsoPWNh__WI8QAIN2xQjawgB4i")



@views.route("/adby")
def adby():
  teachername = "Adby"
  playlist_id = 'PLM-GVlebsoPWZG7j5kRK479fragOS83By'
  with open("website/playlists/adby.txt", 'r', encoding='utf-8') as file:
        content = file.read()
        videos = ast.literal_eval(content)
  return render_template('used_pages/videopage.html',
                         videos=videos,
                         playlist_id=playlist_id,
                         teachername=teachername)


@views.route("/adbyupdate")
def adbyupdate():
    return createtxtfile("adby" , "PLM-GVlebsoPWZG7j5kRK479fragOS83By")




