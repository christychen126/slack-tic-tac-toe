from flask import Flask, request, redirect, jsonify, url_for
import helper
import os
from slackclient import SlackClient
from slacker import Slacker

SLACK_TOKEN = os.environ.get('SLACK_TOKEN')
TOKEN = os.environ.get('BOT_TOKEN')
slack_client = SlackClient(TOKEN)
slacker = Slacker(TOKEN)

app = Flask(__name__)
app.secret_key = "ABC123"  # For example only

channels = {}

entryPositionNames = {
    'top-left': " ",
    'top-middle': " ",
    'top-right': " ",
    'middle-left': " ",
    'middle': " ",
    'middle-right': " ",
    'bottom-left': " ",
    'bottom-middle': " ",
    'bottom-right': " ",
}

currentState = {
    "in_progress": False,
    "creator": " ",
    "invited_user_name": " ",
    "accepted_invite": False,
    "players": {},
    "current_player": " ",
    "winner": False,
    "channel_id": "",
}

# need to make sure I validate keys AND TEAM/CHANNEL ID or one game throughout whole slack test group


@app.route('/', methods=["POST"])
def state():
    channel_id = request.form.get('channel_id')
    # currentState['channel_id'] = channel_id
    channels[channel_id] = {"in_progress": False,
                            "creator": " ",
                            "invited_user_name": " ",
                            "accepted_invite": False,
                            "players": {},
                            "current_player": " ",
                            "winner": False,
                            }
    print channels
    #channel['channel_id'] = {creator, inviter, invited, channel_id} PUT CURRENT STATE INSIDE

    if channels.get("channel_id").get("in_progress") == False:
        user_id = request.form.get('user_id')
        # needed to convert to string to prevent saving user_name as type_unicode
        user_name = str(request.form.get('user_name'))
        invited_player = request.form.get('text')

        if not invited_player:
            return "Please invite someone to play with."

        in_channel = channels['channel_id']
        in_channel['creator'] = user_name
        in_channel['invited_user_name'] = invited_player[1:]
        in_channel['players'][user_name] = {
            "user_name": user_name,
            "user_id": user_id,
            "letter": "X"
        }

        response = slacker.users.list()
        r = response.body['members']

        existing_users = []
        for i in r:
            for key, value in i.iteritems():
                if key == "name":
                    existing_users.append(value)

        # inviting yourself
        if channels.get("channel_id").get("creator") == in_channel.get('invited_user_name'):
            return "You cannot invite yourself to play."

        # inviting someone non-existent in team
        if channels.get("channel_id").get('invited_user_name') not in existing_users:
            return "That username does not exists."

        message = "@%s wants to play Tic-Tac-Toe with @%s. @%s, do you want to /ttt-accept or /ttt-decline?" % \
                  (in_channel['creator'], in_channel['invited_user_name'], in_channel['invited_user_name'])

        return jsonify({
            'response_type': 'in_channel',
            'text': message
            })

    else:
        return "A game is already in session between @%s and @%s. To see the current game," \
               "enter '/ttt-board'" % (in_channel['creator'], in_channel['invited_user_name'])


@app.route('/accept', methods=["POST"])
def accept_invite():
    current_channel = request.form.get("channel_id")

    if current_channel in channels.keys():

        in_channel = channels['current_channel']
        if channels.get("channel_id").get("in_progress") == True:
            return "A game is already in session between @%s and @%s. To see the current game," \
                "enter '/ttt-board'" % (in_channel['creator'], in_channel['invited_user_name'])

        user_id2 = request.form.get('user_id')
        user_name2 = str(request.form.get('user_name'))
        in_channel['current_player'] = user_name2
        in_channel['players'][user_name2] = {
            "user_name": user_name2,
            "user_id": user_id2,
            "letter": "O"
        }

        in_channel['in_progress'] = True
        in_channel['accepted_invite'] = True

        message = "To see available commands, enter /ttt-help."
        slack_client.api_call("chat.postMessage", channel=current_channel, text=message, username='Tic-Tac-Toe', icon_emoji=':robot_face:')

        return redirect(url_for('board', channel_id=current_channel))

    else:
        return "You do not have permission to do this at this time."


@app.route('/decline', methods=["POST"])
def decline():
    current_channel = request.form.get("channel_id")
    if current_channel in channels.keys():
        declined = request.form.get('user_name')

        if channels.get('currenet_channel').get('invited_user_name') == declined and channels.get('current_channel').get("in_progress") == False:
            message = "@%s has declined the game." % channels['currenet_channel']['invited_user_name']
            return jsonify({
                'response_type': 'in_channel',
                'text': message
                })
        else:
            return "You do not have permission to do this at this time."

    else:
        return "You do not have permission to do this at this time."


@app.route('/board')
def board():
    current_channel = request.args.get("channel_id")
    if current_channel in channels.keys() and channels.get('current_channel').get('in_progress') == True:
            message = "```| %s | %s | %s |\n|---+---+---|\n| %s | %s | %s |\n|---+---+---|\n| %s | %s | %s |\n```" \
                % (entryPositionNames['top-left'],
                   entryPositionNames['top-middle'],
                   entryPositionNames['top-right'],
                   entryPositionNames['middle-left'],
                   entryPositionNames['middle'],
                   entryPositionNames['middle-right'],
                   entryPositionNames['bottom-left'],
                   entryPositionNames['bottom-middle'],
                   entryPositionNames['bottom-right'])

            # channel_id = request.args.get('channel_id')
            slack_client.api_call("chat.postMessage", channel=current_channel, text=message, username='Tic-Tac-Toe', icon_emoji=':robot_face:')

            in_channel = channels['current_channel']
            # if there is a winner, end game
            if channels.get('current_channel').get('winner') == True:
                # refreshing necessary currentState keys
                for key in entryPositionNames.keys():
                    entryPositionNames[key] = " "

                helper.restart_board(channels, current_channel)

                return jsonify({
                    'response_type': 'in_channel',
                    'text': ("Game over. @%s wins!" % (in_channel['current_player']))
                    })

            # if board is/is not full but no winners:
            if channels.get('current_channel').get('winner') == False:
                for value in entryPositionNames.values():
                    if value == " ":
                        # #if there are still spaces available, continue
                        # channel_id = request.form.get('channel_id')

                        return jsonify({
                            'response_type': 'in_channel',
                            'text': ("It is @%s's turn!" % (in_channel['current_player']))
                            })

                # when the game ends in a draw:
                helper.restart_board(channels, current_channel)

                return jsonify({
                    'response_type': 'in_channel',
                    'text': "Game over. It's a draw!"
                    })

    else:
        return "You do not have permission to do this at this time."


@app.route('/move', methods=["POST"])
def move():
    current_channel = request.form.get("channel_id")
    if (current_channel in channels.keys()) and (channels.get('current_channel').get('accepted_invite') == True):
        person_submitted = str(request.form.get('user_name'))
        in_channel = channels['current_channel']
        current = in_channel.get('current_player')

        if current == person_submitted:
            position = " "

            # if player submits a text stating a move
            input_position = request.form.get('text')
            if input_position:
                position = input_position

            # check if position is valid
            if position in entryPositionNames:
                currentPositionEntry = entryPositionNames.get(position)
                # when a square is taken
                if currentPositionEntry != " ":
                    return "This square is already taken. Please choose another."

                # choosing an empty square
                else:
                    current_letter = in_channel['players'][person_submitted]['letter']
                    entryPositionNames[position] = current_letter

                    # checks if the move constitues a win
                    if helper.winner(entryPositionNames):
                        in_channel['winner'] = True

                        return redirect(url_for('board', channel_id=current_channel))

                    # switching between current player and other player
                    if channels.get('current_channel').get('current_player') == in_channel['creator']:
                        in_channel['current_player'] = in_channel['invited_user_name']

                    else:
                        in_channel['current_player'] = in_channel['creator']

                    return redirect(url_for('board', channel_id=current_channel))

            else:
                # if it is a wrong move, valid moves are listed out
                valid_moves = []
                for key in entryPositionNames.keys():
                    valid_moves.append(key)

                valid_moves.sort()

                return "Please enter a valid move: %s." % (", ".join(valid_moves))

        else:
            return "Players make a move by entering /ttt-move [position]."

    else:
        return "You do not have permission to do this at this time."


@app.route('/more_help')
def help():
    """ """
    print "I am groot"
    return ("/ttt [@username] -- Invite a person to play Tic-Tac-Toe.\n"
            "/ttt-accept -- Accept the game invitation.\n"
            "/ttt-decline -- Decline the game invitation.\n"
            "/ttt-board -- View the game board.\n"
            "/ttt-move [position] -- Place a letter on an empty square. Positions include"
            "'top-left', 'top-middle', 'top-right', 'middle-left', 'middle-right',"
            "'bottom-left', 'bottom-middle', 'bottom-right'.\n"
            "/ttt-end -- End the game.\n\n"
            "Check out https://en.wikipedia.org/wiki/Tic-tac-toe for more information.")


@app.route('/end_game', methods=["POST"])
def end():
    """ """
    current_channel = request.form.get("channel_id")
    if current_channel in channels.keys() and channels.get('current_channel').get('in_progress') == True:
        for key in entryPositionNames.keys():
            entryPositionNames[key] = " "

        helper.restart_board(channels, current_channel)

        message = "The game has ended."
        return jsonify({
            'response_type': 'in_channel',
            'text': message
            })

    else:
        return "You do not have permission to do this at this time."

if __name__ == '__main__':


    DEBUG = "NO_DEBUG" not in os.environ
    PORT = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
