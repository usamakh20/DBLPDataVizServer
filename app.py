import time
from flask import Flask, json, Response, request, render_template
from collections import Counter
import mysql.connector
from joblib import load

FoR_gnb = load('static/Naive_FoR.joblib')
FoR_clf = load('static/Decision_FoR.joblib')

Journal_gnb = load('static/Naive_Journal.joblib')
Journal_clf = load('static/Decision_Journal.joblib')

Conference_gnb = load('static/Naive_Conference.joblib')
Conference_clf = load('static/Decision_Conference.joblib')

Publication_gnb = load('static/Naive_Publication.joblib')
Publication_clf = load('static/Decision_Publication.joblib')

app = Flask(__name__)

# db_con = mysql.connector.connect(
#     host='34.93.138.139',
#     user='root',
#     passwd='4Jm519N0IgsEvJ2O',
#     database='usama_dblp'
# )

db_con = mysql.connector.connect(
    host='localhost',
    user='root',
    passwd='12345678',
    database='dblp'
)

PREFIX = "/api"
pageLimit = 100

dbCursor = db_con.cursor(buffered=True, dictionary=True)

searchJournal = "SELECT id,name FROM journal"

searchConference = "SELECT id,acronym as `name` FROM conference"

searchFoRNodes = "SELECT id,name as `label` FROM author WHERE FoR_id=%s AND id in (%l)"

searchFoREdges = "SELECT author_id_1 as `from`, author_id_2 as `to`, CONVERT(publications , CHAR(50)) as `label` " \
                 "FROM coauthors_by_FoR " \
                 "WHERE FoR_id=%s AND publications>=%s LIMIT %s,%s"

searchFoREdgesCount = "SELECT COUNT(*) as `count` " \
                      "FROM coauthors_by_FoR " \
                      "WHERE FoR_id=%s AND publications>=%s"

searchCountPublications = "SELECT count(*) as `count` FROM publication"

searchPublications = "SELECT * FROM publication LIMIT %s,%s"

searchFoRs = "SELECT * FROM focus_of_research"

searchFoRsById = "SELECT * FROM focus_of_research where id in (%s)"

searchCountAuthors = "SELECT count(*) as `count` FROM author"

searchAuthors = "SELECT author.id, author.name,focus_of_research.name as `FoR` " \
                "FROM author LEFT JOIN focus_of_research " \
                "ON FoR_id=focus_of_research.id ORDER BY author.id LIMIT %s,%s"

searchAuthorByName = "SELECT author.id, author.name,focus_of_research.name as `FoR` " \
                     "FROM author LEFT JOIN focus_of_research " \
                     "ON FoR_id=focus_of_research.id " \
                     "WHERE author.name LIKE %s LIMIT %s,%s"

searchCountAuthorByName = "SELECT count(*) as `count` FROM author WHERE `name` LIKE %s"

searchCite = "SELECT Count(*) as citations FROM cite WHERE publ_id = %s"

searchJournalCore = "SELECT * FROM core_journal where title like %s order by length(title)"

searchConferenceCore = "SELECT * FROM core_conference where acronym in (%s)"

searchPublicationsAuthors = "SELECT author.id,author.name,focus_of_research.name as `FoR` " \
                            "FROM author_publication, author LEFT JOIN focus_of_research " \
                            "ON FoR_id=focus_of_research.id " \
                            "WHERE publ_id=%s AND author_id=author.id"

searchAuthorsPublications = "SELECT publication.id,`key`,title,`year`,type " \
                            "FROM publication,author_publication " \
                            "WHERE author_id = %s and publication.id = publ_id "

searchAuthorsJournals = "SELECT journal.id,journal.name,Count(*) as `publications` " \
                        "FROM author_publication,publication,journal " \
                        "where author_id = %s and publ_id = publication.id " \
                        "and publication.journal_id = journal.id " \
                        "group by journal.id"

# searchAuthorsConferences = "SELECT SUBSTRING_INDEX(SUBSTRING_INDEX(publication.key,'/',2),'/',-1) as `acronym`," \
#                            "COUNT(*) as `count` " \
#                            "FROM authors_publications,publication " \
#                            "WHERE authors_publications.author_id = %s AND " \
#                            "authors_publications.publ_id = publication.id AND publication.key LIKE 'conf/%' " \
#                            "GROUP BY SUBSTRING_INDEX(SUBSTRING_INDEX(publication.key,'/',2),'/',-1)"

searchAuthorsConferences = "SELECT publication.key,publication.crossref " \
                           "FROM author_publication,publication " \
                           "where author_id = %s and publ_id = " \
                           "publication.id and publication.key like 'conf/%' "


class Middleware():
    """
    Simple WSGI middleware
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if not db_con.is_connected():
            db_con.reconnect()
        return self.app(environ, start_response)


# calling our middleware
app.wsgi_app = Middleware(app.wsgi_app)

dbCursor.execute(searchCountPublications)
publications_count = dbCursor.fetchone()["count"]

dbCursor.execute(searchCountAuthors)
authors_count = dbCursor.fetchone()["count"]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/predict')
def show_predict():
    dbCursor.execute(searchJournal)
    journals = dbCursor.fetchall()
    dbCursor.execute(searchConference)
    conferences = dbCursor.fetchall()
    return render_template('predict.html', FoR=get_for().json, journals=journals, conferences=conferences)


@app.route('/FoRs')
def show_for():
    return render_template('for.html', data=get_for().json)


@app.route('/publications')
def show_publications():
    page = request.args.get('page', default=1, type=int) - 1
    pages = int(publications_count / pageLimit)
    return render_template('publications.html', data=get_publications(page).json, pages=pages + 1, page=page + 1)


@app.route('/publication/<int:publ_id>')
def show_publication(publ_id):
    title = request.args.get('title', default='', type=str)
    type = request.args.get('type', default='', type=str)
    key = request.args.get('key', default='', type=str)
    year = request.args.get('year', default='', type=str)
    authors = get_publication_authors(publ_id).json

    return render_template('publication.html',
                           data={'title': title, 'type': type, 'key': key, 'year': year, 'authors': authors})


@app.route('/search/author/<string:author_name>')
@app.route('/authors')
def show_authors(author_name=''):
    page = request.args.get('page', default=1, type=int) - 1

    if len(author_name) > 0:
        authors = search_author(author_name, page).json
        pages = int(get_search_author_count(author_name).json['count'] / pageLimit)
    else:
        authors = get_authors(page).json
        pages = int(authors_count / pageLimit)
    return render_template('authors.html', data=authors, pages=pages + 1, page=page + 1)


@app.route('/author/<int:author_id>')
def show_author(author_id):
    name = request.args.get('name', default='', type=str)
    FoR = get_author_for(author_id).json
    publications = get_author_publications(author_id).json

    if not FoR:
        FoR = ['None', 0]
    else:
        FoR = FoR[0]

    return render_template('author.html', data={'name': name, 'FoR': FoR, 'publications': publications})


@app.route('/graph/')
@app.route('/graph/<FoR_id>')
def show_graph(FoR_id=801):
    x = request.args.get('x', default=1, type=int)
    name = request.args.get('name', default='', type=str)
    page = request.args.get('page', default=1, type=int) - 1

    offset = pageLimit * page

    dbCursor.execute(searchFoREdgesCount, (FoR_id, x))
    pages = int(dbCursor.fetchone()['count'] / pageLimit)

    dbCursor.execute(searchFoREdges, (FoR_id, x, offset, pageLimit))
    edge_data = dbCursor.fetchall()

    author_ids = []
    for data in edge_data:
        author_ids.append(data['from'])
        author_ids.append(data['to'])

    author_ids_string = '\'' + '\',\''.join(map(str, author_ids)) + '\''
    dbCursor.execute(searchFoRNodes.replace('%l', author_ids_string), (FoR_id,))
    nodes_data = dbCursor.fetchall()

    return render_template('graph.html', data={'x': x, 'id': FoR_id, 'name': name, 'authors': json.dumps(nodes_data),
                                               'coauthors': json.dumps(edge_data)}, pages=pages + 1, page=page + 1)


@app.route(PREFIX + '/predict/<int:clf_id>')
def get_prediction(clf_id):
    id = request.args.get('id', default=8, type=int)
    year = request.args.get('year', default=1980, type=int)
    prediction = {}
    if clf_id == 0:
        prediction['NB'] = [FoR_gnb.predict([[id, year]])[0], FoR_gnb.predict_proba([[id, year]]).max()]
        prediction['DT'] = [FoR_clf.predict([[id, year]])[0], FoR_clf.predict_proba([[id, year]]).max()]

    elif clf_id == 1:
        prediction['NB'] = [Journal_gnb.predict([[id, year]])[0], Journal_gnb.predict_proba([[id, year]]).max()]
        prediction['DT'] = [Journal_clf.predict([[id, year]])[0], Journal_clf.predict_proba([[id, year]]).max()]

    elif clf_id == 2:
        prediction['NB'] = [Conference_gnb.predict([[id, year]])[0], Conference_gnb.predict_proba([[id, year]]).max()]
        prediction['DT'] = [Conference_clf.predict([[id, year]])[0], Conference_clf.predict_proba([[id, year]]).max()]

    else:
        prediction['NB'] = [Publication_gnb.predict([[year]])[0], Publication_gnb.predict_proba([[year]]).max()]
        prediction['DT'] = [Publication_clf.predict([[year]])[0], Publication_clf.predict_proba([[year]]).max()]

    prediction['NB'][1] = str(int(prediction['NB'][1] * 100)) + '%'
    prediction['DT'][1] = str(int(prediction['DT'][1] * 100)) + '%'

    return Response(json.dumps(prediction), mimetype='application/json')


# Most Time taken author_id = 14334, 47415  26 seconds
@app.route(PREFIX + '/FoR/<author_id>')
def get_author_for(author_id):
    # start_time = time.time()

    total_FoRs = Counter()

    dbCursor.execute(searchAuthorsJournals, (author_id,))
    journals = dbCursor.fetchall()

    dbCursor.execute(searchAuthorsConferences, (author_id,))
    conferences = dbCursor.fetchall()

    for row in journals:
        dbCursor.execute(searchJournalCore, ('%'.join(row['name'].replace('.', '').split()) + '%',))
        if dbCursor.rowcount > 0:
            result = dbCursor.fetchone()
            total_FoRs[result['FoR_id']] += row['publications']

    acronyms_count = Counter([conf['key'].split('/')[1] for conf in conferences])
    # acronyms_count = Counter(dict((acronym,count) for acronym,count in conferences))
    if acronyms_count:
        acronyms_string = '\'' + '\',\''.join(list(acronyms_count)) + '\''
        dbCursor.execute(searchConferenceCore.replace('%s', acronyms_string))

        for row in dbCursor:
            total_FoRs[row['FoR_id']] += acronyms_count[row['acronym'].lower()]

    result = Counter()
    if total_FoRs:
        FoRs_string = '\'' + '\',\''.join(list(map(str, total_FoRs))) + '\''
        dbCursor.execute(searchFoRsById.replace('%s', FoRs_string))

        for row in dbCursor:
            result[row['name']] = total_FoRs[row['id']]

    # result["Time Taken"] = round(time.time() - start_time, 3)
    # print("Time Taken: " + str(round(time.time() - start_time, 3)))

    return Response(json.dumps(result.most_common()), mimetype='application/json')
    # return Response(json.dumps(total_FoRs.most_common()), mimetype='application/json')


@app.route(PREFIX + '/authors/<int:page>')
def get_authors(page=0):
    offset = pageLimit * page

    dbCursor.execute(searchAuthors, (offset, pageLimit))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route(PREFIX + '/authors/count')
def get_authors_count():
    dbCursor.execute(searchCountAuthors)
    result = dbCursor.fetchone()

    return Response(json.dumps(result), mimetype='application/json')


@app.route(PREFIX + '/search/author/<string:author_name>/<int:page>')
def search_author(author_name, page=0):
    offset = pageLimit * page

    dbCursor.execute(searchAuthorByName, (author_name + '%', offset, pageLimit))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route(PREFIX + '/search/author/<string:author_name>/count')
def get_search_author_count(author_name):
    dbCursor.execute(searchCountAuthorByName, (author_name + '%',))
    result = dbCursor.fetchone()

    return Response(json.dumps(result), mimetype='application/json')


@app.route(PREFIX + '/FoRs')
def get_for():
    dbCursor.execute(searchFoRs)
    result = dbCursor.fetchall()
    return Response(json.dumps(result), mimetype='application/json')


@app.route(PREFIX + '/publications/count')
def get_publications_count():
    dbCursor.execute(searchCountPublications)
    result = dbCursor.fetchone()

    return Response(json.dumps(result), mimetype='application/json')


@app.route(PREFIX + '/publications/<int:page>')
def get_publications(page=0):
    offset = pageLimit * page

    dbCursor.execute(searchPublications, (offset, pageLimit))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route(PREFIX + '/publication/<int:publ_id>/authors')
def get_publication_authors(publ_id):
    dbCursor.execute(searchPublicationsAuthors, (publ_id,))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route(PREFIX + '/publication/<int:publ_id>/cite')
def get_cite(publ_id):
    dbCursor.execute(searchCite, (publ_id,))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route(PREFIX + '/author/<int:author_id>/publications')
def get_author_publications(author_id):
    dbCursor.execute(searchAuthorsPublications, (author_id,))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


if __name__ == '__main__':
    app.run(debug=True)
    dbCursor.close()
    db_con.close()
