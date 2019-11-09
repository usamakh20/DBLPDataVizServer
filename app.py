from flask import Flask, json, Response, request, render_template
from collections import Counter
import mysql.connector

app = Flask(__name__)

db_con = mysql.connector.connect(
    host='34.93.138.139',
    user='root',
    passwd='4Jm519N0IgsEvJ2O'
)

PREFIX = "/api"
pageLimit = 100

dbCursor = db_con.cursor(buffered=True, dictionary=True)

searchFoRNodes = "SELECT id,authors_name as `label` FROM dblp.for_authors WHERE for_id=%s AND id in (%l)"

searchFoREdges = "SELECT author1 as `from`, author2 as `to`, CONVERT(publications , CHAR(50)) as `label` " \
                 "FROM coauthors.graph_data " \
                 "WHERE for_id=%s AND publications>=%s LIMIT 100"

searchPublications = "SELECT * FROM dblp.publication LIMIT %s,%s"

searchFoRs = "SELECT * FROM `FoR`.`FoR`"

searchFoRsById = "SELECT * FROM `FoR`.`FoR` where id in (%s)"

searchAuthors = "SELECT for_authors.id, authors_name as `name`,`FoR`.name as `FoR` " \
                "FROM dblp.for_authors,`FoR`.`FoR` " \
                "WHERE for_id=`FoR`.id ORDER BY id LIMIT %s,%s "

searchAuthorsById = "SELECT * FROM dblp.authors where id = %s"

searchAuthorByName = "SELECT for_authors.id, authors_name as `name`,`FoR`.name as `FoR` " \
                     "FROM dblp.for_authors,`FoR`.`FoR`" \
                     "WHERE for_id =`FoR`.id AND authors_name LIKE %s LIMIT %s,%s"

searchCountAuthorByName = "SELECT count(*) as count FROM dblp.authors WHERE `name` LIKE %s"

searchCite = "SELECT Count(*) as citations FROM dblp.cite WHERE publ_id = %s"

searchJournalFoR = "SELECT * FROM `FoR`.journal where title like %s order by length(title)"

searchConferenceFoR = "SELECT * FROM `FoR`.conference where acronym in (%s)"

searchPublicationsAuthors = "SELECT for_authors.id,for_authors.authors_name as `name`,`FoR`.`name` as `FoR` " \
                            "FROM dblp.authors_publications,dblp.for_authors,`FoR`.`FoR` " \
                            "WHERE publ_id=%s AND author_id=for_authors.id AND `FoR`.id = for_id"

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
def index():
    return render_template('index.html')


@app.route('/FoRs')
def show_for():
    return render_template('for.html', data=get_for().json)


@app.route('/publications')
def show_publications():
    return render_template('publications.html', data=get_publications().json)


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
    if len(author_name) > 0:
        authors = search_author(author_name).json
    else:
        authors = get_authors().json
    return render_template('authors.html', data=authors)


@app.route('/author/<int:author_id>')
def show_author(author_id):
    name = request.args.get('name', default='', type=str)
    FoR = request.args.get('FoR', default='', type=str)
    publications = get_author_publications(author_id).json

    return render_template('author.html', data={'name': name, 'FoR': FoR, 'publications': publications})


@app.route('/graph/')
@app.route('/graph/<FoR_id>')
def graph(FoR_id=None):
    x = request.args.get('x', default=1, type=int)
    name = request.args.get('name', default='', type=str)

    if not FoR_id:
        FoR_id = 999

    dbCursor.execute(searchFoREdges,(FoR_id,x))
    edge_data = dbCursor.fetchall()

    authorids = []
    for data in edge_data:
        authorids.append(data['from'])
        authorids.append(data['to'])

    authorids_string = '\'' + '\',\''.join(map(str, authorids)) + '\''
    dbCursor.execute(searchFoRNodes.replace('%l', authorids_string),(FoR_id,))
    nodes_data = dbCursor.fetchall()

    authors = [{"id": 1664843, "label": "\"Johann\" Sebastian Rudolph"},
               {"id": 2361734, "label": "'Anau Mesui"},
               {"id": 458683, "label": "'Maseka Lesaoana"},
               {"id": 893586, "label": "'Niran Adetoro"},
               {"id": 2361027, "label": "'Yinka Oyerinde"}]
    coauthors = [{'from': 458683, 'to': 1664843, 'label': '20'},
                 {'from': 893586, 'to': 2361027, 'label': '4'},
                 {'from': 2361734, 'to': 893586, 'label': '7'},
                 {'from': 893586, 'to': 1664843, 'label': '1'}]

    return render_template('graph.html', data={'x': x, 'id': FoR_id, 'name': name, 'authors': json.dumps(nodes_data),
                                               'coauthors': json.dumps(edge_data)})


@app.route(PREFIX + '/FoR/<author_id>')
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


@app.route(PREFIX + '/authors')
def get_authors():
    page = request.args.get('page', default=0, type=int)
    offset = pageLimit * page

    dbCursor.execute(searchAuthors, (offset, pageLimit))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route(PREFIX + '/search/author/<string:author_name>')
def search_author(author_name):
    page = request.args.get('page', default=0, type=int)
    offset = pageLimit * page

    dbCursor.execute(searchAuthorByName, (author_name + '%', offset, pageLimit))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route(PREFIX + '/search/author/<string:author_name>/count')
def get_search_author_count(author_name):
    dbCursor.execute(searchCountAuthorByName, (author_name + '%',))
    result = dbCursor.fetchall()

    return Response(json.dumps(result), mimetype='application/json')


@app.route(PREFIX + '/FoRs')
def get_for():
    dbCursor.execute(searchFoRs)
    result = dbCursor.fetchall()
    return Response(json.dumps(result), mimetype='application/json')


@app.route(PREFIX + '/publications')
def get_publications():
    page = request.args.get('page', default=0, type=int)
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
