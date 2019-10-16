from flask import Flask, json, Response, request
import mysql.connector

app = Flask(__name__)

dblp = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd='12345678',
    database="dblp"
)

FoR = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd='12345678',
    database="FoR"
)

pageLimit = 100

FoRCursor = FoR.cursor(buffered=True,dictionary=True)
dblpCursor = dblp.cursor(buffered=True,dictionary=True)

searchPublications = "SELECT * FROM dblp.publication LIMIT %s,%s"

searchFoRs = "SELECT * FROM `FoR`.`FoR`"

searchAuthors = "SELECT id,name FROM dblp.authors ORDER BY id LIMIT %s,%s"

searchAuthorsById = "SELECT * FROM dblp.authors where id = %s"

searchCite = "SELECT Count(*) as citations FROM dblp.cite WHERE publ_id = %s"

searchAuthorsPublications = "SELECT publication.id,`key`,title,`year` " \
                            "FROM dblp.publication,dblp.authors,dblp.authors_publications " \
                            "WHERE dblp.authors.id = %s and dblp.authors.id = authors_publications.author_id and " \
                            "publication.id = authors_publications.publ_id; "

searchAuthorsJournals = "SELECT journal.id,dblp.journal.name,Count(*) as `No of publications` " \
                        "FROM dblp.authors_publications,dblp.publication,journal " \
                        "where authors_publications.author_id = %s and authors_publications.publ_id = publication.id and " \
                        "publication.journal_id = journal.id " \
                        "group by journal.id"

searchAuthorsConferences = "SELECT dblp.publication.key,dblp.publication.crossref " \
                           "FROM dblp.authors_publications,dblp.publication " \
                           "where authors_publications.author_id = %s and authors_publications.publ_id = publication.id and " \
                           "publication.key like 'conf/%' "


@app.route('/')
def welcome():
    return 'Welcome To DBLP Visualization'

@app.route('/journals/<author_id>')
def get_journals(author_id):
    dblpCursor.execute(searchAuthorsJournals, (author_id,))
    result = []
    for (id, name, publications) in dblpCursor:
        result.append({
            "id": id,
            "name": name,
            "No. Of Publications": publications
        })
    return Response(json.dumps(result), mimetype='application/json')


@app.route('/author')
def get_authors():
    page = request.args.get('page', default=0, type=int)
    offset = pageLimit * page

    dblpCursor.execute(searchAuthors, (offset, pageLimit))
    result = dblpCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route('/for')
def get_FoRs():
    dblpCursor.execute(searchFoRs)
    result = dblpCursor.fetchall()
    return Response(json.dumps(result), mimetype='application/json')


@app.route('/publication')
def get_publications():
    page = request.args.get('page', default=0, type=int)
    offset = pageLimit * page

    dblpCursor.execute(searchPublications,(offset, pageLimit))
    result = dblpCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')

# @app.route('/publication/cite')
# def get_cite():
#     dblpCursor.execute(searchPublications,(offset, pageLimit))
#     result = dblpCursor.fetchall()
#
#     return Response(json.dumps(result), mimetype='application/json')


if __name__ == '__main__':
    app.run()
    dblpCursor.close()
    FoRCursor.close()
    dblp.close()
    FoR.close()
