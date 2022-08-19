from re import split
from flask import Flask, render_template, url_for, request, redirect, session, Response
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import mariadb
import ast
import csv 
import io
import os
from flask_mail import Mail, Message

app = Flask(__name__)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 465
app.config["MAIL_USERNAME"] = "miloss1301@gmail.com"
app.config["MAIL_PASSWORD"] = "sifra123"
app.config["MAIL_USE_TLS"] = False
app.config["MAIL_USE_SSL"] = True
mail = Mail(app)

def send_email(ime, prezime, email, lozinka):
	msg = Message(
		subject="Korisnički nalog",
		sender="ATVSS Evidencija studenata",
		recipients=[email],
	)
	msg.html = render_template("email.html", ime=ime, prezime=prezime, lozinka=lozinka)
	mail.send(msg)
	return "Sent"

app.secret_key = "tajni_kljuc"

# deklaracija upload direktorijuma
UPLOAD_FOLDER = "static/uploads/"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

konekcija = mysql.connector.connect(
password="",
user="root",
database="evidencija_studenata",
port=3310,
auth_plugin='mysql_native_password'
)

kursor = konekcija.cursor(dictionary=True)

def ulogovan():
	if "ulogovani_korisnik" in session:
		return True
	else:
		return False

def rola():
	if ulogovan():
		return ast.literal_eval(session["ulogovani_korisnik"]).pop("rola")


############### LOGIN ########################### 
@app.route("/", methods=["GET","POST"])
def login():
	if request.method =="GET":
		return render_template("login.html")
	if request.method == "POST":
		forma = request.form
		vrednost = (forma["email"],)
		upit = """ SELECT * FROM korisnici WHERE email=%s """
		kursor.execute(upit,vrednost)
		korisnik = kursor.fetchone()
		if korisnik != None:
			if check_password_hash(korisnik["lozinka"], forma["lozinka"]):
				session["ulogovani_korisnik"] = str(korisnik)
				return redirect(url_for("korisnici"))
			else:
				return render_template("login.html")
		else:
			return render_template("login.html")

@app.route('/logout')
def logout():
	session.pop('ulogovan_korisnik',None)
	return redirect(url_for('login'))
##################### EXPORT #####################
@app.route("/export/<tip>")
def export(tip):
	switch = {
		"studenti": "SELECT * FROM studenti",
		"korisnici": "SELECT * FROM korisnici",
		"predmeti": "SELECT * FROM predmeti",
	}
	upit = switch.get(tip)
	kursor.execute(upit)
	rezultat = kursor.fetchall()
	output = io.StringIO()
	writer = csv.writer(output)
	for row in rezultat:
		red = [ ]
		for value in row.values():
			red.append(str(value))
		writer.writerow(red)
	output.seek(0)
	return Response(
		output,
		mimetype="text/csv",
		headers={"Content-Disposition": "attachment;filename=" + tip + ".csv"},
	)
################### Korisnici #########################(Sve radi)
@app.route("/korisnici", methods=["GET"])
def korisnici():
	if ulogovan():
		if rola() == "profesor":
			return redirect("studenti")
		else:
			upit = "SELECT * FROM korisnici LIMIT 10 OFFSET %s"
			strana = request.args.get("page", "1")
			offset = int(strana) * 10 - 10
			prethodna_strana = ""
			sledeca_strana = "/korisnici?page=2"
			if "=" in request.full_path:
				split_path = request.full_path.split("=")
				del split_path[-1]
				sledeca_strana = "=".join(split_path) + "=" + str(int(strana) + 1)
				prethodna_strana = "=".join(split_path) + "=" + str(int(strana) - 1)
			vrednost = (offset,)
			kursor.execute(upit, vrednost)
			korisnici = kursor.fetchall()
			return render_template("korisnici.html", korisnici=korisnici, strana=strana, sledeca_strana=sledeca_strana,prethodna_strana=prethodna_strana)
	
	else:
		return redirect(url_for("login"))

@app.route("/korisnik_novi", methods=["GET","POST"])
def korisnikn():
	if ulogovan():
		if rola() == "profesor":
			return redirect(url_for("studenti"))
		else:
			if request.method == "GET":
				return render_template("korisnik_novi.html")
			if request.method == "POST":
				forma = request.form
				hesovana_lozinka = generate_password_hash(forma["lozinka"])
				vrednosti = (
					forma["ime"],
					forma["prezime"],
					forma["email"],
					forma["rola"],
					hesovana_lozinka
				)
				upit = """  INSERT INTO 
							korisnici(ime,prezime,email,rola,lozinka)
							VALUES (%s,%s,%s,%s,%s)
				"""
				kursor.execute(upit, vrednosti)
				konekcija.commit()
				#send_email(forma["ime"], forma["prezime"], forma["email"], forma["lozinka"])
				return redirect(url_for("korisnici"))
			return render_template("korisnik_novi.html")
	else:
		return redirect(url_for("login"))

@app.route("/korisnik_izmena/<id>", methods=["GET","POST"])
def korisnik_izmena(id):
	if ulogovan():
		if rola() == "profesor":
			return redirect(url_for("studenti"))
		else:
			if request.method=='GET':
				upit = """ SELECT * FROM korisnici WHERE id=%s """
				vrednost=(id,)
				kursor.execute(upit,vrednost)
				korisnik=kursor.fetchone()
				return render_template("korisnik_izmena.html", korisnik=korisnik)
			if request.method=='POST':
				forma=request.form
				hesovana_lozinka=generate_password_hash(forma["lozinka"])
				vrednosti = ( forma["ime"], forma["prezime"], forma["email"], hesovana_lozinka, forma["rola"], id)
				upit=""" UPDATE korisnici SET
    		    		 ime=%s,
    		    		 prezime=%s,
    		    		 email=%s,
    		    		 lozinka=%s,
    		    		 rola=%s
    		    		 WHERE id=%s
    		    """
				kursor.execute(upit,vrednosti)
				konekcija.commit()
				return redirect(url_for("korisnici"))
	else:
		return redirect(url_for("login"))

@app.route("/korisnik_brisanje/<id>", methods=["POST"])
def korisnik_brisanje(id):
	if ulogovan():
		if rola() == "profesor":
			return redirect(url_for("korisnici"))
		else:
			upit = " DELETE FROM korisnici WHERE id=%s"
			vrednost = (id,)
			kursor.execute(upit,vrednost)
			konekcija.commit()
			return redirect(url_for("korisnici"))
	else:
		return redirect(url_for("login"))

################## Predmeti #################(Sve radi)
@app.route("/predmeti", methods=["GET"])
def predmeti():
	if ulogovan():
		if rola() == "profesor":
			return redirect(url_for("studenti"))
		else:
			upit = "SELECT * FROM predmeti LIMIT 10 OFFSET %s"
			strana = request.args.get("page", "1")
			offset = int(strana) * 10 - 10
			prethodna_strana = ""
			sledeca_strana = "/predmeti?page=2"
			if "=" in request.full_path:
				split_path = request.full_path.split("=")
				del split_path[-1]
				sledeca_strana = "=".join(split_path) + "=" + str(int(strana) + 1)
				prethodna_strana = "=".join(split_path) + "=" + str(int(strana) - 1)
			vrednost = (offset,)
			kursor.execute(upit, vrednost)
			predmet = kursor.fetchall()
			return render_template("predmeti.html", predmeti=predmet, strana=strana, sledeca_strana=sledeca_strana,prethodna_strana=prethodna_strana)
	else:
		return redirect(url_for("login"))

@app.route("/predmet_izmena/<id>", methods=["GET","POST"])
def predmet_izmena(id):
	if ulogovan():
		if rola() == "profesor":
			return redirect(url_for("studenti"))
		else:
			if request.method=='GET':
				upit = """ SELECT * FROM predmeti WHERE id=%s """
				vrednost=(id,)
				kursor.execute(upit,vrednost)
				predmet=kursor.fetchone()
				return render_template("predmet_izmena.html", predmet=predmet)
			if request.method=='POST':
				forma=request.form
				vrednosti = (
					forma["sifra"],
					forma["naziv"],
					forma["godina_studija"],
					forma["espb"],
					forma["obavezni_izborni"],
					id
				)
				upit=""" UPDATE predmeti SET
    		    		 sifra=%s,
    		    		 naziv=%s,
    		    		 godina_studija=%s,
    		    		 espb=%s,
    		    		 obavezni_izborni=%s
    		    		 WHERE id=%s
    		    """
				kursor.execute(upit,vrednosti)
				konekcija.commit()
				return redirect(url_for("predmeti"))
	else:
		return redirect(url_for("login"))

@app.route("/predmet_novi", methods=["GET","POST"])
def predmetn():
	if ulogovan():
		if rola() == "profesor":
			return redirect(url_for("studenti"))
		else:
			if request.method == "GET":
				return render_template("predmet_novi.html")
			if request.method == "POST":
				forma = request.form
				vrednosti = (
					forma["sifra"],
					forma["naziv"],
					forma["espb"],
					forma["godina_studija"],
					forma["obavezni_izborni"],
				)
				upit = """  INSERT INTO 
							predmeti(sifra,naziv,espb,godina_studija,obavezni_izborni)
							VALUES (%s,%s,%s,%s,%s)
				"""
				kursor.execute(upit, vrednosti)
				konekcija.commit()
				return redirect(url_for("predmeti"))
	else:
		return redirect(url_for("login"))

@app.route("/predmet_brisanje/<id>", methods=["POST"])
def predmet_brisanje(id):
	if ulogovan():
		if rola() == "profesor":
			return redirect(url_for("studenti"))
		else:
			upit = " DELETE FROM predmeti WHERE id=%s"
			vrednost = (id,)
			kursor.execute(upit,vrednost) 
			konekcija.commit()
			return redirect(url_for("predmeti"))
	else:
		return redirect(url_for("login"))

#################### STUDENT #####################
@app.route("/studenti", methods=["GET"])
def studenti():
	if ulogovan():
		strana = request.args.get("page", "1")
		offset = int(strana) * 5 - 5
		prethodna_strana = ""
		sledeca_strana = "/studenti?page=2"
		if "=" in request.full_path:
			split_path = request.full_path.split("=")
			del split_path[-1]
			sledeca_strana = "=".join(split_path) + "=" + str(int(strana) + 1)
			prethodna_strana = "=".join(split_path) + "=" + str(int(strana) - 1)
		args = request.args.to_dict()
		order_by = "id"
		order_type = "asc"
		if "order_by" in args:
			order_by = args["order_by"].lower()
			if (
				"prethodni_order_by" in args
				and args["prethodni_order_by"] == args["order_by"]
				):
				if args["order_type"] == "asc":
					order_type = "desc"
		s_ime = "%%"
		s_prezime = "%%"
		s_broj_indeksa = "%%"
		s_god_studija = "%%"
		s_prosek_ocena_od = "0"
		s_prosek_ocena_do = "10"
		if "prosek_ocena_od" in args:
			if args["prosek_ocena_od"]=="":
				s_prosek_ocena_od = "0"
			else:
				s_prosek_ocena_od = args["prosek_ocena_od"]
		if "prosek_ocena_do" in args:
			if args["prosek_ocena_do"]=="":
				s_prosek_ocena_do = "10"
			else:
				s_prosek_ocena_do = args["prosek_ocena_do"]
		s_espb_od ="0"
		s_espb_do = "240"
		if "espb_od" in args:
			if args["espb_od"]=="":
				s_espb_od = "0"
			else:
				s_espb_od = args["espb_od"]
		if "espb_do" in args:
			if args["espb_do"]=="":
				s_espb_do = "240"
			else:
				s_espb_do = args["espb_do"]
		if "ime" in args:
			s_ime = "%" + args["ime"] + "%"
		if "prezime" in args:
			s_prezime = "%" + args["prezime"] + "%"
		if "broj_indeksa" in args:
			s_broj_indeksa = "%" + args["broj_indeksa"] + "%"
		if "god_studija" in args:
			s_god_studija = "%" + args["god_studija"] + "%"
		
		upit = "SELECT * FROM studenti WHERE ime LIKE %s AND prezime LIKE %s AND broj_indeksa LIKE %s AND godina_studija LIKE %s AND espb >= %s AND espb <= %s AND prosek_ocena >= %s AND prosek_ocena <= %s ORDER BY " + order_by + " " + order_type + " LIMIT 5 OFFSET %s"
		vrednosti = (
			s_ime,
			s_prezime,
			s_broj_indeksa,
			s_god_studija,
			s_espb_od,
			s_espb_do,
			s_prosek_ocena_od,
			s_prosek_ocena_do,
			offset,
			)
		kursor.execute(upit, vrednosti)
		studenti = kursor.fetchall()
		return render_template("studenti.html", studenti = studenti, rola = rola(), strana=strana, sledeca_strana=sledeca_strana, prethodna_strana=prethodna_strana, order_type=order_type, args = args)
	else:
		return redirect(url_for("login"))

@app.route("/student_novi", methods=["GET","POST"])
def studentn():
	if ulogovan():
		if rola() == "administrator":
			if request.method == "GET":
				return render_template("student_novi.html")
			if request.method == "POST":
				forma = request.form
				naziv_slike = ""
				if "slika" in request.files:
					file = request.files["slika"]
					if file.filename:
						naziv_slike = forma["jmbg"] + file.filename
						file.save(os.path.join(app.config["UPLOAD_FOLDER"], naziv_slike))
				vrednosti = (
					forma["ime"],
					forma["ime_roditelja"],
					forma["prezime"],
					forma["broj_indeksa"],
					forma["godina_studija"],
					forma["jmbg"],
					forma["datum"],
					forma["espb"],
					forma["prosek_ocena"],
					forma["broj_telefona"],
					forma["email"],
					naziv_slike
				)
				upit = """  INSERT INTO 
							studenti(ime,ime_roditelja,prezime,broj_indeksa,godina_studija,jmbg,datum,espb,prosek_ocena,broj_telefona,email,slika)
							VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
				"""
				kursor.execute(upit, vrednosti)
				konekcija.commit() 
				return redirect(url_for("studenti"))
		else:
			return redirect(url_for("studenti"))
	else:
		return redirect(url_for("login"))

@app.route("/student_izmena/<id>", methods=["GET","POST"])
def student_izmena(id):
	if ulogovan():
		if rola() == "administrator":
			if request.method=='GET':
				upit = """ SELECT * FROM studenti WHERE id=%s """
				vrednost=(id,)
				kursor.execute(upit,vrednost)
				student=kursor.fetchone()
				return render_template("student_izmena.html", student=student)
			if request.method=='POST':
				forma = request.form
				naziv_slike = ""
				if "slika" in request.files:
					file = request.files["slika"]
					if file.filename:
						naziv_slike = forma["jmbg"] + file.filename
						file.save(os.path.join(app.config["UPLOAD_FOLDER"], naziv_slike))
				vrednosti = (
					forma["ime"],
					forma["ime_roditelja"],
					forma["prezime"],
					forma["broj_indeksa"],
					forma["godina_studija"],
					forma["jmbg"],
					forma["datum"],
					forma["espb"],
					forma["prosek_ocena"],
					forma["broj_telefona"],
					forma["email"],
					naziv_slike,
					id
				)
				upit = """ UPDATE studenti SET
							ime=%s,
							ime_roditelja=%s,
							prezime=%s,
							broj_indeksa=%s,
							godina_studija=%s,
							jmbg=%s,
							datum=%s,
							espb=%s,
							prosek_ocena=%s,
							broj_telefona=%s,
							email=%s,
							slika=%s
							WHERE id=%s"""
				kursor.execute(upit,vrednosti)
				konekcija.commit()
				return redirect(url_for("studenti"))
		else:
			return redirect(url_for("studenti"))
	else:
		return redirect(url_for("login"))

@app.route("/student_brisanje/<id>", methods=["POST"])
def student_brisanje(id):
	if ulogovan():
		if rola() == "administrator":
			upit = " DELETE FROM studenti WHERE id=%s"
			vrednost = (id,)
			kursor.execute(upit,vrednost)
			konekcija.commit()
			return redirect(url_for("studenti"))
		else:
			return redirect(url_for("studenti"))
	else:
		return redirect(url_for("login"))

@app.route("/student/<id>", methods=["GET"])
def student(id):
	if ulogovan():
		if request.method=="GET":
			upit = "SELECT * FROM studenti WHERE id=%s"
			vrednost = (id,)
			kursor.execute(upit,vrednost)
			student = kursor.fetchone()
			upit = """SELECT predmeti.sifra, predmeti.naziv, predmeti.godina_studija, predmeti.espb, predmeti.obavezni_izborni, ocene.ocena, ocene.datum,ocene.id
					   FROM ocene INNER JOIN predmeti ON ocene.predmet_id = predmeti.id 
					   WHERE student_id=%s
					"""
			vrednost = (id,)
			kursor.execute(upit,vrednost)
			ocena = kursor.fetchall()
			upit = "SELECT * FROM predmeti"
			kursor.execute(upit)
			predmet = kursor.fetchall()
			return render_template("student.html", student=student, ocene=ocena, predmeti=predmet)
	else:
		return redirect(url_for("login"))

#####################  OCENA  ##############
@app.route("/ocena_nova/<id>", methods=['POST']) 
def ocena_nova(id):
    if ulogovan():
        upit="""
            INSERT INTO ocene(student_id,predmet_id,ocena,datum)
            VALUES(%s,%s,%s,%s)
        """
        forma=request.form
        vrednosti=(id, forma['predmet_id'],forma['ocena'],forma['datum'])
        kursor.execute(upit, vrednosti)
        konekcija.commit()

        upit="SELECT AVG(ocena) AS rezultat FROM ocene WHERE student_id=%s"
        vrednost=(id,)
        kursor.execute(upit,vrednost)
        prosek_ocena=kursor.fetchone()

        upit="SELECT SUM(espb) AS rezultat FROM predmeti WHERE id IN (SELECT predmet_id FROM ocene WHERE student_id=%s)"
        vrednost=(id,)
        kursor.execute(upit,vrednost)
        espb=kursor.fetchone()

        upit="UPDATE studenti SET espb=%s,prosek_ocena=%s WHERE id=%s"
        vrednosti=(espb['rezultat'],prosek_ocena['rezultat'],id)
        kursor.execute(upit,vrednosti)
        konekcija.commit()
        return redirect(url_for('student',id=id))
    else:
        return redirect(url_for('login'))

@app.route("/ocena_izmena/<id>/<ocena_id>",methods=["GET","POST"])
def ocena_izmena(id,ocena_id):
    if ulogovan():
        if request.method=='GET':
            upit="SELECT * FROM studenti WHERE id=%s"
            vrednost=(id,)
            kursor.execute(upit,vrednost)
            student=kursor.fetchone()

            upit="SELECT * FROM predmeti"
            kursor.execute(upit)
            predmeti=kursor.fetchall()

            upit="SELECT predmeti.sifra,predmeti.naziv,predmeti.godina_studija,predmeti.obavezni_izborni,predmeti.espb,ocene.ocena,ocene.id FROM ocene JOIN predmeti on ocene.predmet_id=predmeti.id WHERE student_id=%s"
            vrednost=(id,)
            kursor.execute(upit,vrednost)
            ocene=kursor.fetchall()

            upit="SELECT * FROM ocene WHERE id=%s"
            vrednost=(ocena_id,)
            kursor.execute(upit,vrednost)
            data_ocena=kursor.fetchone()
            return render_template("ocena_izmena.html",predmeti=predmeti,ocene=ocene,data_ocena=data_ocena,id=id,student=student)
        elif request.method=='POST':
            forma=request.form

            vrednosti=(
            forma['predmet_id'],
            forma['ocena'],
            forma['datum'],
            ocena_id,
            )

            upit=""" UPDATE ocene SET
            predmet_id=%s,
            ocena=%s,
            datum=%s 
            WHERE id=%s
            """
            kursor.execute(upit,vrednosti)

            upit="SELECT AVG(ocena) AS rezultat FROM ocene WHERE student_id=%s"
            vrednost=(id,)
            kursor.execute(upit,vrednost)
            prosek_ocena=kursor.fetchone()

            upit="SELECT SUM(espb) AS rezultat FROM predmeti WHERE id IN(SELECT predmet_id FROM ocene WHERE student_id=%s)"
            vrednost=(id,)
            kursor.execute(upit,vrednost)
            espb=kursor.fetchone()

            upit="UPDATE studenti SET espb=%s,prosek_ocena=%s WHERE id=%s"
            vrednosti=(espb['rezultat'],prosek_ocena['rezultat'],id)
            kursor.execute(upit,vrednosti)
            konekcija.commit()
            return redirect(url_for("student",id=id))
    else:
        return redirect(url_for('login'))

@app.route("/ocena_brisanje/<id>/<ocena_id>",methods=['GET','POST'])
def ocena_brisanje(id,ocena_id):
	if ulogovan():
		if rola()=='administrator':
			upit="""DELETE FROM ocene WHERE id=%s
			"""
			vrednost=(ocena_id,)
			kursor.execute(upit, vrednost)

			upit="SELECT AVG(ocena) AS rezultat FROM ocene WHERE student_id=%s"
			vrednost=(id,)
			kursor.execute(upit,vrednost)
			prosek_ocena=kursor.fetchone()

			upit="SELECT SUM(espb) AS rezultat FROM predmeti WHERE id IN (SELECT predmet_id FROM ocene WHERE student_id=%s)"
			vrednost=(id,)
			kursor.execute(upit,vrednost)
			espb=kursor.fetchone()

			upit="UPDATE studenti SET espb=%s, prosek_ocena=%s WHERE id=%s"
			vrednosti=(espb['rezultat'],prosek_ocena['rezultat'],id)
			kursor.execute(upit, vrednosti)

			konekcija.commit()
			return redirect(url_for("student",id=id))
		else:
			return redirect(url_for("studenti"))
	else:
		return redirect(url_for('login'))


#pokretanje aplikacije
app.run(debug=True)