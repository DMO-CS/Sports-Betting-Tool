from flask import Flask, request, render_template
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
import pandas as pd

app = Flask(__name__)

def get_player_id(player_name):
    player_dict = players.find_players_by_full_name(player_name.title())
    if player_dict:
        return player_dict[0]['id']
    return None

def fetch_player_stats(player_name, stat='PTS', statline=20):
    player_id = get_player_id(player_name)
    if not player_id:
        return f"Player '{player_name}' not found."

    seasons = ['2024-25', '2023-24', '2022-23']
    results = []

    for season in seasons:
        # Fetch game logs
        game_log = playergamelog.PlayerGameLog(player_id=player_id, season=season)
        game_df = game_log.get_data_frames()[0]

        total_games = len(game_df)
        if total_games == 0:
            results.append(f"No games found for {season}.")
            continue

        # Calculate based on the stat type
        if stat == 'PRA':
            over_statline_games = len(game_df[game_df['PTS'] + game_df['REB'] + game_df['AST'] > statline])
            stat_label = "Points + Rebounds + Assists"
        elif stat == 'PA':
            over_statline_games = len(game_df[game_df['PTS'] + game_df['AST'] > statline])
            stat_label = "Points + Assists"
        elif stat == 'PR':
            over_statline_games = len(game_df[game_df['PTS'] + game_df['REB'] > statline])
            stat_label = "Points + Rebounds"
        elif stat == 'RA':
            over_statline_games = len(game_df[game_df['REB'] + game_df['AST'] > statline])
            stat_label = "Rebounds + Assists"
        else:
            game_df[stat] = pd.to_numeric(game_df[stat], errors='coerce')
            over_statline_games = len(game_df[game_df[stat] > statline])
            stat_label = stat

        percentage_over = (over_statline_games / total_games) * 100
        results.append(
            f"{player_name} has gone over {statline} {stat_label} in "
            f"{over_statline_games}/{total_games} games ({percentage_over:.2f}%) in the {season} season. - - -"
        )

    return "\n".join(results)

@app.route("/", methods=["GET", "POST"])
def home():
    result = ""
    if request.method == "POST":
        player_name = request.form["player_name"]
        #season = request.form["season"]
        stat_choice = request.form["stat_choice"]
        statline = float(request.form["statline"])

        stat_map = {
            "1": "PTS",
            "2": "AST",
            "3": "REB",
            "4": "STL",
            "5": "BLK",
            "6": "PRA",
            "7": "PA",
            "8": "PR",
            "9": "RA"
        }
        stat = stat_map.get(stat_choice, "PTS")
        result = fetch_player_stats(player_name, stat, statline)

    return render_template("index.html", result=result)

if __name__ == "__main__":
    app.run(debug=True, host= '0.0.0.0')
