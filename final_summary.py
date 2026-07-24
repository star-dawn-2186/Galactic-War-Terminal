import json
import pandas as pd
def generate_kill_stats_table(file_path):

    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not find the file '{file_path}'.")
        return

    player_stats = []

    for player_name, stats in data.items():
        kills_list = stats.get("KILLS", [])
        
        if not kills_list:
            continue
            
        total_kills = sum(kills_list)
        num_missions = len(kills_list)
        average_kills = total_kills / num_missions
        
        player_stats.append({
            "Player": player_name,
            "Total Kills": total_kills,
            "Missions": num_missions,
            "Avg Kills/Mission": average_kills
        })


    player_stats.sort(key=lambda x: x["Total Kills"], reverse=True)

    # Print the formatted table
    print(f"{'Player Name':<35} | {'Total Kills':<12} | {'Missions':<10} | {'Avg Kills/Mission'}")
    print("-" * 82)
    
    for stat in player_stats:
        print(f"{stat['Player']:<35} | {stat['Total Kills']:<12} | {stat['Missions']:<10} | {stat['Avg Kills/Mission']:.2f}")
    df = pd.DataFrame(player_stats)
    df.to_csv("output.csv", index=False)
if __name__ == "__main__":

    json_filename = 'm04_11_overwhelming success.json'
    generate_kill_stats_table(json_filename)