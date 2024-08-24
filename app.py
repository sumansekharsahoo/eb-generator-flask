from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import math
import hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = "brundabansumansekhar"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///ebrecord.sqlite3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
# app.app_context().push()


class ebrecord(db.Model):
    __tablename__ = "ebrecord"

    rid = db.Column(db.Integer, primary_key=True)
    m1 = db.Column(db.Integer)
    m2 = db.Column(db.Integer)
    m3 = db.Column(db.Integer)
    p = db.Column(db.Integer)
    a1 = db.Column(db.Integer)
    a2 = db.Column(db.Integer)
    b1 = db.Column(db.Integer)
    b2 = db.Column(db.Integer)
    c1 = db.Column(db.Integer)
    c2 = db.Column(db.Integer)

    def __repr__(self):
        return f"[{self.rid},{self.m1},{self.m2},{self.m3},{self.a1},{self.a2},{self.b1},{self.b2},{self.c1},{self.c2}]"


migrate = Migrate(app, db)


@app.route("/", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        pwd = request.form["password"]
        hasher = hashlib.sha256()
        hasher.update(pwd.encode())
        if (
            hasher.hexdigest()
            == "a47f9feb93f011ce426dc4540c666ff7afd41ad45435d6fb64949938835182d8"
        ):
            session["login"] = True
            return redirect(url_for("home"))
        else:
            return redirect(url_for("login"))
    else:
        return render_template("index.html")


months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sept",
    "Oct",
    "Nov",
    "Dec",
]
current_month = datetime.now().month
current_year = datetime.now().year - 2000
bill_for = f"Electricity bill for {months[(current_month-2)%12]}'{current_year}-{months[(current_month-1)%12]}'{current_year}"


class MainMeter:
    def __init__(self, name, prev, now):
        self.name = name
        self.prev = prev
        self.now = now
        self.read = now - prev
        self._diff = None

    def setDiff(self, sum_of_meters):
        self._diff = self.read - sum_of_meters

    def getDiff(self):
        return self._diff

    def getECval(self):
        if self.read <= 50:
            return [self.read, 0, 0, 0]
        elif self.read <= 200:
            return [50, self.read - 50, 0, 0]
        elif self.read <= 400:
            return [50, 150, self.read - 200, 0]
        else:
            return [50, 150, 200, self.read - 400]


class House:
    def __init__(self, name, prev, now):
        self.name = name
        self.prev = prev
        self.now = now
        self.read = now - prev
        self._unit = None
        self._unitCStr = None

    def setUnit(self, diff_share, pump_share):
        self._unit = self.read + diff_share + pump_share
        self._unitCStr = (
            str(self.read)
            + "+"
            + str(diff_share)
            + "+"
            + str(pump_share)
            + "="
            + str(self._unit)
        )

    def getUnit(self):
        return self._unit

    def getUnitCStr(self):
        return self._unitCStr


class EClass:
    def __init__(self, limit_pm, rate, m1, m2, m3, unitsRemain, nextleft):
        self.rate = rate
        self.limit_pm = limit_pm  # per meter (50,150,200....)
        self.totalunit = m1 + m2 + m3
        self.totalval = self.totalunit * rate
        self.prevRemain = unitsRemain
        self._rowDet = None
        self._rowVal = None
        self.unitsAlloted = [0, 0, 0, 0, 0, 0]
        self.distb = [m1, m2, m3]

        ct = 0
        nonNeg = {}
        for i in range(len(unitsRemain)):
            if unitsRemain[i] > 0:
                ct += 1
                nonNeg[i] = unitsRemain[i]

        # def amp(arr):
        #     x = True
        #     for i in arr:
        #         x &= i
        #     return x

        def belowAvg(dict, avg):  # return index (unitsRemain) of those <avg
            x = []
            for i in dict:
                if dict[i] < avg:
                    x.append(i)
            return x

        if ct > 0 and nextleft:
            # state=[False]*ct
            totUnit = self.totalunit
            avgUnit = totUnit / ct
            ctBelowAvg = belowAvg(nonNeg, avgUnit)
            while len(ctBelowAvg) > 0:
                for i in ctBelowAvg:
                    self.unitsAlloted[i] += nonNeg[i]
                    totUnit -= nonNeg[i]
                    ct -= 1
                    del nonNeg[i]
                    if ct:
                        avgUnit = totUnit / ct
                        ctBelowAvg = belowAvg(nonNeg, avgUnit)
            for i in nonNeg:
                self.unitsAlloted[i] += avgUnit
        else:
            if not nextleft:
                for i in nonNeg:
                    self.unitsAlloted[i] = nonNeg[i]

    def getUnitRemain(self):
        x = []
        for i in range(len(self.prevRemain)):
            x.append(self.prevRemain[i] - self.unitsAlloted[i])
        return x

    def setRowDet(self):
        self._rowDet = []
        self._rowVal = []
        totalAllot = round(
            self.unitsAlloted[0]
            + self.unitsAlloted[1]
            + self.unitsAlloted[2]
            + self.unitsAlloted[3]
            + self.unitsAlloted[4]
            + self.unitsAlloted[5],
            2,
        )
        asPB = (
            str(self.distb[0])
            + "+"
            + str(self.distb[1])
            + "+"
            + str(self.distb[2])
            + "="
            + str(self.totalunit)
            + "*"
            + str(self.rate)
            + "="
            + str(round(self.totalunit * self.rate, 2))
        )

        # asPB = (
        #     str(round(self.unitsAlloted[0] + self.unitsAlloted[1], 2))
        #     + "+"
        #     + str(round(self.unitsAlloted[3] + self.unitsAlloted[5], 2))
        #     + "+"
        #     + str(round(self.unitsAlloted[2] + self.unitsAlloted[4], 2))
        #     + "="
        #     + str(totalAllot)
        #     + "*"
        #     + str(self.rate)
        #     + "="
        #     + str(round(totalAllot * self.rate, 2))
        # )

        self._rowVal.append(round(totalAllot * self.rate, 2))
        self._rowDet.append(asPB)
        for i in self.unitsAlloted:
            if i == 0:
                mstr = "-"
                self._rowVal.append(0)
            else:
                mstr = (
                    str(round(i, 2))
                    + "*"
                    + str(self.rate)
                    + "="
                    + str(round(self.rate * i, 2))
                )
                self._rowVal.append(round(self.rate * i, 2))
            self._rowDet.append(mstr)

    def getRowDet(self):
        return self._rowDet

    def getRowVal(self):
        return self._rowVal


@app.route("/home", methods=["POST", "GET"])
def home():
    if "login" in session:
        if request.method == "POST":
            now_m1 = int(request.form["m1_present"])
            now_m2 = int(request.form["m2_present"])
            now_m3 = int(request.form["m3_present"])
            now_p = int(request.form["p_present"])
            now_a1 = int(request.form["a1_present"])
            now_a2 = int(request.form["a2_present"])
            now_b1 = int(request.form["b1_present"])
            now_b2 = int(request.form["b2_present"])
            now_c1 = int(request.form["c1_present"])
            now_c2 = int(request.form["c2_present"])
            prev_m1 = int(request.form["m1_prev"])
            prev_m2 = int(request.form["m2_prev"])
            prev_m3 = int(request.form["m3_prev"])
            prev_p = int(request.form["p_prev"])
            prev_a1 = int(request.form["a1_prev"])
            prev_a2 = int(request.form["a2_prev"])
            prev_b1 = int(request.form["b1_prev"])
            prev_b2 = int(request.form["b2_prev"])
            prev_c1 = int(request.form["c1_prev"])
            prev_c2 = int(request.form["c2_prev"])
            extra_csv = request.form["extra"]
            misc_csv = request.form["misc"]
            if extra_csv == "":
                extra = [0, 0, 0, 0, 0, 0]
            else:
                extra_slist = extra_csv.split(",")
                extra = []
                for i in extra_slist:
                    extra.append(float(i))
            if misc_csv == "":
                misc = [0, 0, 0, 0, 0, 0]
            else:
                misc_slist = misc_csv.split(",")
                misc = []
                for i in misc_slist:
                    misc.append(float(i))

            m1 = MainMeter("METER 1", prev_m1, now_m1)
            m2 = MainMeter("METER 2", prev_m2, now_m2)
            m3 = MainMeter("METER 3", prev_m3, now_m3)

            a1 = House("A1", prev_a1, now_a1)
            a2 = House("A2", prev_a2, now_a2)
            b1 = House("B1", prev_b1, now_b1)
            b2 = House("B2", prev_b2, now_b2)
            c1 = House("C1", prev_c1, now_c1)
            c2 = House("C2", prev_c2, now_c2)

            read_p = now_p - prev_p
            pump_div = math.ceil(read_p / 6)
            pump_distb = round(pump_div, 2)

            m1.setDiff(a1.read + a2.read + read_p)
            m2.setDiff(b2.read + c2.read)
            m3.setDiff(b1.read + c1.read)

            a1.setUnit(m1.getDiff() / 2, pump_distb)
            a2.setUnit(m1.getDiff() / 2, pump_distb)
            b1.setUnit(m3.getDiff() / 2, pump_distb)
            c1.setUnit(m3.getDiff() / 2, pump_distb)
            b2.setUnit(m2.getDiff() / 2, pump_distb)
            c2.setUnit(m2.getDiff() / 2, pump_distb)
            session["meter"] = [
                [m1.now, m1.prev, m1.read],
                [m2.now, m2.prev, m2.read],
                [m3.now, m3.prev, m3.read],
                [now_p, prev_p, read_p],
                bill_for,
            ]
            session["house"] = [
                [a1.now, a1.prev, a1.read, a1.getUnitCStr()],
                [a2.now, a2.prev, a2.read, a2.getUnitCStr()],
                [b1.now, b1.prev, b1.read, b1.getUnitCStr()],
                [b2.now, b2.prev, b2.read, b2.getUnitCStr()],
                [c1.now, c1.prev, c1.read, c1.getUnitCStr()],
                [c2.now, c2.prev, c2.read, c2.getUnitCStr()],
            ]
            m1.read += extra[0] + extra[1]
            m2.read += extra[3] + extra[5]
            m3.read += extra[2] + extra[4]
            ec_m1 = m1.getECval()
            ec_m2 = m2.getECval()
            ec_m3 = m3.getECval()
            if ec_m1[1] + ec_m2[1] + ec_m3[1] == 0:
                nextMark = False
            else:
                nextMark = True

            ec3 = EClass(
                50,
                3,
                ec_m1[0],
                ec_m2[0],
                ec_m3[0],
                [
                    a1.getUnit() + extra[0],
                    a2.getUnit() + extra[1],
                    b1.getUnit() + extra[2],
                    b2.getUnit() + extra[3],
                    c1.getUnit() + extra[4],
                    c2.getUnit() + extra[5],
                ],
                nextMark,
            )
            ec3_allot = ec3.getUnitRemain()

            if ec_m1[2] + ec_m2[2] + ec_m3[2] == 0:
                nextMark = False
            else:
                nextMark = True
            ec48 = EClass(150, 4.8, ec_m1[1], ec_m2[1], ec_m3[1], ec3_allot, nextMark)
            ec48_allot = ec48.getUnitRemain()
            if ec_m1[3] + ec_m2[3] + ec_m3[3] == 0:
                nextMark = False
            else:
                nextMark = True

            ec58 = EClass(200, 5.8, ec_m1[2], ec_m2[2], ec_m3[2], ec48_allot, nextMark)
            ec58_allot = ec58.getUnitRemain()
            ec62 = EClass(700, 6.2, ec_m1[3], ec_m2[3], ec_m3[3], ec58_allot, False)

            ec3.setRowDet()
            ec48.setRowDet()
            ec58.setRowDet()
            ec62.setRowDet()
            mfc = 120

            val3 = ec3.getRowVal()
            val48 = ec48.getRowVal()
            val58 = ec58.getRowVal()
            val62 = ec62.getRowVal()
            tval = []
            edval = []
            edmfcval = []
            rebval = []
            swpval = 1200
            swparr = [swpval]
            misc_sum = 0
            for i in misc:
                misc_sum += i
            misc.insert(0, misc_sum)
            finaltot = []
            mfc_i = [120, 20, 20, 20, 20, 20, 20]
            for i in range(7):
                tval.append(round(val3[i] + val48[i] + val58[i] + val62[i], 2))
                edval.append(round(tval[i] * 0.04, 2))
                edmfcval.append(round(tval[i] + edval[i] + mfc_i[i], 2))
                rebval.append(round(-0.02 * edmfcval[i], 2))
                swparr.append(round(swpval / 6, 2))
                finaltot.append(round(edmfcval[i] + rebval[i] + swparr[i] + misc[i]))

            swparr.pop()

            session["final"] = [
                [str(mfc), str(mfc / 6)],
                ec3.getRowDet(),
                ec48.getRowDet(),
                ec58.getRowDet(),
                ec62.getRowDet(),
                tval,
                edval,
                edmfcval,
                rebval,
                swparr,
                misc,
                finaltot,
            ]
            return redirect(url_for("result"))
        else:
            return render_template("home.html")
    else:
        return redirect(url_for("login"))


@app.route("/result")
def result():
    if "login" in session:
        if "meter" in session:
            return render_template(
                "result.html",
                meter=session["meter"],
                house=session["house"],
                final=session["final"],
            )
        else:
            return redirect(url_for("home"))
    else:
        return redirect(url_for("login"))


if __name__ == "__main__":
    # db.create_all()
    app.run(debug=False)
