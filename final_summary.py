import json
import pandas as pd
def generate_kill_stats_table(file_path):
    # Load the JSON data
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not find the file '{file_path}'.")
        return

    player_stats = []

    # Iterate through the JSON to calculate totals and averages
    for player_name, stats in data.items():
        kills_list = stats.get("SHOTS FIRED", [])
        
        if not kills_list:
            continue
            
        total_kills = sum(kills_list)
        num_missions = len(kills_list)
        average_kills = total_kills / num_missions
        
        player_stats.append({
            "Player": player_name,
            "Total Shots Fired": total_kills,
            "Missions": num_missions,
            "Avg Shots Fired/Mission": average_kills
        })

    # Sort the list by Total Kills in descending order
    player_stats.sort(key=lambda x: x["Total Shots Fired"], reverse=True)

    # Print the formatted table
    print(f"{'Player Name':<35} | {'Total Shots Fired':<12} | {'Missions':<10} | {'Avg Shots Fired/Mission'}")
    print("-" * 82)
    
    for stat in player_stats:
        print(f"{stat['Player']:<35} | {stat['Total Shots Fired']:<12} | {stat['Missions']:<10} | {stat['Avg Shots Fired/Mission']:.2f}")
    df = pd.DataFrame(player_stats)
    df.to_csv("output.csv", index=False)
if __name__ == "__main__":
    # Replace with your actual file name if it differs
    json_filename = 'm04_10_success.json'
    generate_kill_stats_table(json_filename)