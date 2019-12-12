# DBLPDataVizServer
A REST server in FLASK to query and visualize data from dblp stored in MYSQL.


If you want to run locally follow steps below:

1. To run flask make sure you have python, flask and mysql installed.
2. Your mysql server should be running locally and contain the dblp database.
3. See https://github.com/usamathescientist/dblp for more info.
4. Ensure all the packages in requirements.txt are installed.
5. cd into the project folder and run the commands below. 

$ 'export FLASK_APP=app.py'
$ 'python -m flask run'

After running flask go to http://127.0.0.1:5000/ to view the app.
