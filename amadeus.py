from flask import Flask, render_template, request
from database import Database
import amadeus_prompts
from chaingang import Amadeus
import yaml
import argparse

with open('./config.yaml', 'r') as f:
    config = yaml.safe_load(f)

prompt = amadeus_prompts.summarizer_template

def nl2br(value):
    return value.replace('\n', '<br>\n')
app = Flask(__name__)

app.jinja_env.filters['nl2br'] = nl2br

@app.route('/')

def home():
    clear = app.config.get('CLEAR', False)
    with Database("chatlog.db", config.get('session_id')) as db:
        db.create_table(recreate=clear)
        chatlog = db.fetch_data()
    return render_template('index.html', chatlog=chatlog)

print ("Finished setting up homepage and loading history.")


@app.route('/get_response', methods=['POST'])
def get_response():
    try:
        with Database("chatlog.db", config.get('session_id')) as db:
            ama = Amadeus(config=config, verbose=True)
            user_input = request.form['input']
            db.insert_data("You", user_input)

            try:
                chatbot_response = ama.invoke(user_input)
                db.insert_data("Amadeus", chatbot_response)
                return chatbot_response
            except Exception as e:
                error_msg = f"I'm sorry, I encountered an error: {str(e)}"
                db.insert_data("Amadeus", error_msg)
                return error_msg
    except Exception as e:
        app.logger.error(f"Database error: {str(e)}")
        return "I'm sorry, I'm having trouble accessing my memory right now."


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--listen', action="store_true", help="Set to listen mode.")
    parser.add_argument('--port', "-p", type=int, default=8085, help="Server port (default: 8085).")
    parser.add_argument('--clear', action="store_true", default=False, help="Clear and reinitialize chatlog database.")

    args = parser.parse_args()

    app.config['CLEAR'] = args.clear

    if args.listen:
        host_addr = "0.0.0.0"
    else:
        host_addr = "127.0.0.1"

    app.run(host=host_addr, port=args.port)

if __name__ == '__main__':
    main()

