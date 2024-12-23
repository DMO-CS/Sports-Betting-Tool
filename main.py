from flask import Flask, request, render_template
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

def create_bar_graph(percentages, seasons):
    # Define bar colors based on the threshold
    colors = ['green' if pct > 50 else 'red' for pct in percentages]

    # Create the bar plot
    plt.figure(figsize=(5, 4))
    plt.bar(seasons, percentages, color=colors)
    plt.axhline(50, color='black', linestyle='--', linewidth=1)  # Add a threshold line at 50%
    plt.title('Performance by Season')
    plt.ylabel('Percentage Over Threshold (%)')
    plt.xlabel('Season')
    
    plt.gca().set_facecolor('burlywood')  # Axes background
    plt.gcf().set_facecolor('burlywood')  # Figure background

    # Save the plot to a BytesIO object
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plt.close()

    # Encode the image to base64 for embedding in HTML
    graph_url = base64.b64encode(img.getvalue()).decode()
    return f"data:image/png;base64,{graph_url}"

def get_player_id(player_name):
    player_dict = players.find_players_by_full_name(player_name.title())
    if player_dict:
        return player_dict[0]['id']
    return None

def fetch_player_stats(player_name, stat='PTS', statline=20, team=None):
    player_id = get_player_id(player_name)
    if not player_id:
        return f"Player '{player_name}' not found."

    seasons = ['2024-25', '2023-24', '2022-23']
    results = []
    resultsTeam = []
    percentages = [] # for graphing
    iterator = 0

    for season in seasons:
        # Fetch game logs
        game_log = playergamelog.PlayerGameLog(player_id=player_id, season=season)
        game_df = game_log.get_data_frames()[0]

        total_games = len(game_df)
        if total_games == 0:
            results.append(f"No games found for {season}.")
            percentages.append(0)
            continue

        # Calculate based on the stat type
        def calculate_over_statline(df, stat):
            if df is None or len(df) == 0:
                return 0
            if stat == 'PRA':
                return len(df[df['PTS'] + df['REB'] + df['AST'] > statline])
            elif stat == 'PA':
                return len(df[df['PTS'] + df['AST'] > statline])
            elif stat == 'PR':
                return len(df[df['PTS'] + df['REB'] > statline])
            elif stat == 'RA':
                return len(df[df['REB'] + df['AST'] > statline])
            else:
                df.loc[:,stat] = pd.to_numeric(df[stat], errors='coerce')
                return len(df[df[stat] > statline])

        over_statline_games = calculate_over_statline(game_df, stat)
        percentage_over = (over_statline_games / total_games) * 100 if total_games > 0 else 0
        percentages.append(percentage_over)
        
        results.append(
            f"|* * * * * {player_name} went OVER {statline} {stat} in {over_statline_games}/{total_games} games "
            f"({percentage_over:.2f}%) ---> {season} season. * * * * *|<br><br>"
        )
        
        # Filter by team if specified
        if team:
            game_tf = game_df[game_df['MATCHUP'].str.contains(team.upper())]
            total_games_tf = len(game_tf)
            if total_games_tf > 0:
                tf_over = calculate_over_statline(game_tf, stat)
                percentage_over_tf = (tf_over / total_games_tf) * 100
                results.pop(iterator)
                results.append(
                    f"|* * * * * {player_name} went OVER {statline} {stat} in {over_statline_games}/{total_games} games "
                    f"({percentage_over:.2f}%) ---> {season} season. * * * * *|"
                    f"|* * * * * {player_name} went OVER {statline} {stat} in {tf_over}/{total_games_tf} games "
                    f"({percentage_over_tf:.2f}%) ONLY against {team.upper()} in the {season} season. * * * * *|<br><br>"
                )
        iterator = iterator + 1
        
    
    while len(percentages) < 3:
        percentages.append(0)
    return "".join(results), percentages

@app.route("/", methods=["GET", "POST"])
def home():
    result = ""
    graph_url = None #initialization
    if request.method == "POST":
        player_name = request.form["player_name"]
        #season = request.form["season"]
        stat_choice = request.form["stat_choice"]
        statline = float(request.form["statline"])
        team = request.form["team"].strip() if "team" in request.form else None

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
        result, percentages = fetch_player_stats(player_name, stat, statline, team)
        
        seasons = ['2024-25', '2023-24', '2022-23']
        graph_url = create_bar_graph(percentages, seasons)

    return render_template("index.html", result=result, graph_url=graph_url)

if __name__ == "__main__":
    app.run(debug=True, host= '0.0.0.0')
