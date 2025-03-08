# setup

make run
make shell (in another terminal window)
 - ask configure --no-browser
   * sign in to amazon
   * copy the authorization code from the browser window into the CLI prompt
   * associate AWS Profile with ASK CLI - Yes
     - Create an IAM user with sufficient permissions to do the things you want in your app
       i.e: s3, lambda, IAM, and.. DynamoDb etc.
 - ask new
   (creates the new skill skeleton)
   - Interactive model
   - python
   - AWS Lambda
   - Hello World
   - skill name
   - skill_path
 - move all files from <skill path> to cwd
   mv <skill_path>/.ask/* .ask && rm -rf <skill_path>/.aask
   mv <skill_path>/* . && rmdir <skill_path>
 - ask deploy
 - ask dialog
 - YAHOO  
