from flask import Flask, json, Response, request
from collections import Counter
import mysql.connector

app = Flask(__name__)


db_con = mysql.connector.connect(
    host='34.93.138.139',
    user='root',
    passwd = '4Jm519N0IgsEvJ2O'
)

pageLimit = 100

dbCursor = db_con.cursor(buffered=True, dictionary=True)

searchPublications = "SELECT * FROM dblp.publication LIMIT %s,%s"

searchFoRs = "SELECT * FROM `FoR`.`FoR`"

searchFoRsById = "SELECT * FROM `FoR`.`FoR` where id in (%s)"

searchAuthors = "SELECT id,name FROM dblp.authors ORDER BY id LIMIT %s,%s"

searchAuthorsById = "SELECT * FROM dblp.authors where id = %s"

searchAuthorByName = "SELECT id,name FROM dblp.authors WHERE `name` LIKE %s LIMIT %s,%s"

searchCountAuthorByName = "SELECT count(*) as count FROM dblp.authors WHERE `name` LIKE %s"

searchCite = "SELECT Count(*) as citations FROM dblp.cite WHERE publ_id = %s"

searchJournalFoR = "SELECT * FROM `FoR`.journal where title like %s order by length(title)"

searchConferenceFoR = "SELECT * FROM `FoR`.conference where acronym in (%s)"

searchPublicationsAuthors = "SELECT dblp.authors.id,dblp.authors.name " \
                            "FROM dblp.publication,dblp.authors,dblp.authors_publications " \
                            "where publication.id = %s and publication.id = authors_publications.publ_id and " \
                            "authors_publications.author_id = authors.id "

searchAuthorsPublications = "SELECT publication.id,`key`,title,`year`,type " \
                            "FROM dblp.publication,dblp.authors_publications " \
                            "WHERE authors_publications.author_id = %s and publication.id = " \
                            "authors_publications.publ_id "

searchAuthorsJournals = "SELECT journal.id,dblp.journal.name,Count(*) as `No. of publications` " \
                        "FROM dblp.authors_publications,dblp.publication,dblp.journal " \
                        "where authors_publications.author_id = %s and authors_publications.publ_id = publication.id " \
                        "and publication.journal_id = journal.id " \
                        "group by journal.id"

searchAuthorsConferences = "SELECT dblp.publication.key,dblp.publication.crossref " \
                           "FROM dblp.authors_publications,dblp.publication " \
                           "where authors_publications.author_id = %s and authors_publications.publ_id = " \
                           "publication.id and publication.key like 'conf/%' "


@app.route('/')
def welcome():
    return 'Welcome To DBLP Visualization'


@app.route('/FoR/<author_id>')
def get_author_for(author_id):
    total_FoRs = Counter()

    dbCursor.execute(searchAuthorsJournals, (author_id,))
    journals = dbCursor.fetchall()

    dbCursor.execute(searchAuthorsConferences, (author_id,))
    conferences = dbCursor.fetchall()

    for row in journals:
        dbCursor.execute(searchJournalFoR, ('%'.join(row['name'].replace('.', '').split()) + '%',))
        if dbCursor.rowcount > 0:
            result = dbCursor.fetchone()
            total_FoRs[result['FoR']] += row['No. of publications']

    acronyms_count = Counter([conf['key'].split('/')[1] for conf in conferences])
    acronyms_string = '\'' + '\',\''.join(list(acronyms_count)) + '\''
    dbCursor.execute(searchConferenceFoR.replace('%s', acronyms_string))

    for row in dbCursor:
        total_FoRs[row['FoR']] += acronyms_count[row['acronym'].lower()]

    FoRs_string = '\'' + '\',\''.join(list(map(str, total_FoRs))) + '\''
    dbCursor.execute(searchFoRsById.replace('%s', FoRs_string))
    result = {}
    for row in dbCursor:
        result[row['name']] = total_FoRs[row['id']]

    return Response(json.dumps(result), mimetype='application/json')


@app.route('/authors')
def get_authors():
    page = request.args.get('page', default=0, type=int)
    offset = pageLimit * page

    dbCursor.execute(searchAuthors, (offset, pageLimit))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route('/search/author/<string:author_name>')
def search_author(author_name):
    page = request.args.get('page', default=0, type=int)
    offset = pageLimit * page

    dbCursor.execute(searchAuthorByName, (author_name + '%', offset, pageLimit))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route('/search/author/<string:author_name>/count')
def get_search_author_count(author_name):
    dbCursor.execute(searchCountAuthorByName, (author_name + '%',))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route('/FoRs')
def get_for():
    dbCursor.execute(searchFoRs)
    result = dbCursor.fetchall()
    return Response(json.dumps(result), mimetype='application/json')


@app.route('/publications')
def get_publications():
    page = request.args.get('page', default=0, type=int)
    offset = pageLimit * page

    dbCursor.execute(searchPublications, (offset, pageLimit))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route('/publication/<int:publ_id>/authors')
def get_publication_authors(publ_id):
    dbCursor.execute(searchPublicationsAuthors, (publ_id,))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route('/publication/<int:publ_id>/cite')
def get_cite(publ_id):
    dbCursor.execute(searchCite, (publ_id,))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route('/author/<int:author_id>/publications')
def get_author_publications(author_id):
    dbCursor.execute(searchAuthorsPublications, (author_id,))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


if __name__ == '__main__':
    app.run(debug=True)
    dbCursor.close()
    db_con.close()
