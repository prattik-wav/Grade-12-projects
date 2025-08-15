class HandCricketDB:
    def __init__(self, config):
        self.DB_CONFIG = config
        self._db = None
        self.current_user = None

    def create_database(self):
        try:
            sql_server = mysql.connector.connect(
                host=self.DB_CONFIG["host"],
                user=self.DB_CONFIG["user"],
                password=self.DB_CONFIG["password"],
            )
            cursor = sql_server.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.DB_CONFIG['database']}")                                                                                                                                                                                                           
            cursor.close()
            sql_server.close()
            print(f"Database '{self.DB_CONFIG['database']}' has been created/loaded successfully.")
        except Error as e:
            print(f"Database could not be created due to error: {e}")
            exit(1)

    def get_db(self):
        try:
            if self._db is None or not self._db.is_connected():
                if self._db:
                    self._db.close()
                self._db = mysql.connector.connect(**self.DB_CONFIG, buffered = True)
            return self._db
        except mysql.connector.Error as error:
            print(f"Database connection error: {error}")
            return None

    def init_db(self):
        ddl_profile = """
            CREATE TABLE IF NOT EXISTS player_profile ( 
                id               INT AUTO_INCREMENT PRIMARY KEY, 
                name             VARCHAR(100) UNIQUE NOT NULL,
                password         VARCHAR(100) NOT NULL, 
                lifetime_runs    INT  DEFAULT 0, 
                lifetime_wickets INT  DEFAULT 0, 
                total_matches    INT  DEFAULT 0, 
                total_wins       INT  DEFAULT 0, 
                total_losses     INT  DEFAULT 0, 
                total_draws      INT  DEFAULT 0,
                lifetime_balls_faced INT  DEFAULT 0,
                lifetime_balls_bowled INT  DEFAULT 0,
                lifetime_runs_conceded INT  DEFAULT 0,
                centuries        INT  DEFAULT 0,
                half_centuries   INT  DEFAULT 0,
                avg_runs         FLOAT  DEFAULT 0.0
            )
            """
        ddl_match_data = """
            CREATE TABLE IF NOT EXISTS match_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                player_name VARCHAR(100) NOT NULL,
                runs INT  DEFAULT 0,
                wickets INT  DEFAULT 0,
                balls_faced INT  DEFAULT 0,
                player_balls_bowled INT  DEFAULT 0,
                player_runs_conceded INT  DEFAULT 0,
                result VARCHAR(10),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_player_name (player_name)
            )
            """
            
        db = self.get_db()
        if db:
            cur = db.cursor()
            try:
                cur.execute(ddl_profile)
                cur.execute(ddl_match_data)
                db.commit()
            finally:
                cur.close()

    def get_password(self, player_name):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute("SELECT password FROM player_profile WHERE name = %s", (player_name,))
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None

    def update_password(self, player_name, new_password):
        db = self.get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE player_profile SET password = %s WHERE name = %s", (new_password, player_name))
        db.commit()
        cursor.close()

    def save_profile(self, profile: dict, player_name: str = "", password: str = None):
        if not player_name:
            raise ValueError("player name must be provided")

        sql = """
              INSERT INTO player_profile
              (name, password, lifetime_runs, lifetime_wickets, total_matches,
               total_wins, total_losses, total_draws, avg_runs, lifetime_balls_faced, lifetime_balls_bowled, lifetime_runs_conceded,
               centuries, half_centuries)
              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
              ON DUPLICATE KEY UPDATE
                password = VALUES(password),
                lifetime_runs = VALUES(lifetime_runs),
                lifetime_wickets = VALUES(lifetime_wickets),
                total_matches = VALUES(total_matches),
                total_wins = VALUES(total_wins),
                total_losses = VALUES(total_losses),
                total_draws = VALUES(total_draws),
                avg_runs = VALUES(avg_runs),
                lifetime_balls_faced = VALUES(lifetime_balls_faced),
                lifetime_balls_bowled = VALUES(lifetime_balls_bowled),
                lifetime_runs_conceded = VALUES(lifetime_runs_conceded),
                centuries = VALUES(centuries),
                half_centuries = VALUES(half_centuries)
              """
        vals = (
            player_name,
            password,
            profile["Lifetime runs"],
            profile["Lifetime wickets"],
            profile["Total Matches Played"],
            profile["Total Wins"],
            profile["Total Losses"],
            profile["Total Draws"],
            profile["Average Runs per Match"],
            profile.get("Lifetime Balls Faced", 0), 
            profile.get("Lifetime Balls Bowled", 0), 
            profile.get("Lifetime Runs Conceded", 0),
            profile.get("Centuries", 0),            
            profile.get("Half Centuries", 0), 
        )
        cur = None
        try:
            db = self.get_db()
            cur = db.cursor()
            cur.execute(sql, vals)
            db.commit()
        
        except KeyError as e:
            print(f"Missing required field in profile: {e}")
        except Exception as e:
            print(f"Failed to save profile: {e}")
            try:
                self.get_db().rollback()
            except:
                pass
        finally:
            try:
                if cur:
                    cur.close()
            except:
                pass

    def save_match_data(self, game_var: dict, player_name: str, player_runs_conceded: int, player_balls_bowled: int, player_match_wickets: int):
        try:
            db = self.get_db()
            cursor = db.cursor()
            sql = """
                INSERT INTO match_data (player_name, runs, wickets, balls_faced, player_runs_conceded, player_balls_bowled, result)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            match_runs = game_var.get('player_runs_1stinn', 0) + game_var.get('player_runs_2ndinn', 0)
            match_wickets = player_match_wickets 
            match_balls_faced = game_var.get("balls_played_by_player", 0)

            values = (
                player_name,
                match_runs,
                match_wickets,
                match_balls_faced,
                player_runs_conceded,
                player_balls_bowled,
                game_var.get("match_result", "unknown"),     
            )
            cursor.execute(sql, values)
            db.commit()
            cursor.close()
        except Exception as e:
            print(f"Error saving match data: {e}")

    def load_profile(self, player_name):
        try:
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute("""
                SELECT lifetime_runs, lifetime_wickets, total_matches, 
                    total_wins, total_losses, total_draws, avg_runs,
                    lifetime_balls_faced, lifetime_balls_bowled, centuries, half_centuries, lifetime_runs_conceded
                FROM player_profile WHERE name = %s
            """, (player_name,))
            row = cursor.fetchone()
            cursor.close()
            if row:
                return {
                    "lifetime_runs": row[0],
                    "lifetime_wickets": row[1],
                    "total_matches_played": row[2],
                    "total_wins": row[3],
                    "total_losses": row[4],
                    "total_draws": row[5],
                    "average_runs_per_match": row[6],
                    "lifetime_balls_faced": row[7],   
                    "lifetime_balls_bowled": row[8],  
                    "centuries": row[9],              
                    "half_centuries": row[10],
                    "lifetime_runs_conceded": row[11]
                }
        except Exception as e:
            print(f"Error loading profile from database: {e}")
        return None

    def player_exists(self, player_name: str):
        try:
            db = self.get_db()
            cursor = db.cursor()
            cursor.execute("SELECT 1 FROM player_profile WHERE name = %s", (player_name,))
            result = cursor.fetchone()
            cursor.close()
            return result is not None
        except Exception as e:
            print(f"Error checking player existence: {e}")
            return False

    def close_db(self):
        try:
            if self._db:
                self._db.close()
                self._db = None
        except:
            pass
class GameDataManager:
    def __init__(self, json_folder_path: str, excel_folder_path: str, player_name: str):
        self.json_folder_path = json_folder_path
        self.excel_folder_path = excel_folder_path
        self.name = player_name

    def calculate_strike_rate(self, runs, balls_faced):
        if balls_faced == 0:
            return 0.0
        
        return round((runs / balls_faced) * 100, 2)
    
    def calculate_economy_rate(self, runs_conceded, balls_bowled):
        if balls_bowled == 0:
            return 0.0
        
        return round((runs_conceded / balls_bowled) * 6, 2)

    def file_exists(self):
        filename = f"{self.name}_game_save.json"
        full_path = f"{self.json_folder_path}/{filename}"
        try:
            with open(full_path, 'r'):
                return True
        except FileNotFoundError:
            return False

    def save_game_to_file(self, game_var):
        filename = f"{self.name}_game_save.json"
        full_path = f"{self.json_folder_path}/{filename}"
        try:
            with open(full_path, 'w') as file:
                json.dump(game_var, file, indent=4)
            print(f"Game saved successfully to {filename}")
        except Exception as e:
            print(f"Error saving game: {e}")

    def load_game_from_file(self):
        filename = f"{self.name}_game_save.json"
        full_path = f"{self.json_folder_path}/{filename}"
        try:
            with open(full_path, 'r') as file:
                loaded_data = json.load(file)
            defaults = {
                'half_centuries': 0,
                'centuries': 0
            }
            for key, value in defaults.items():
                loaded_data.setdefault(key, value)
            print(f"Game loaded successfully from {filename}")
            return loaded_data
        except FileNotFoundError:
            print(f"No save file found: {filename}")
            return None
        except Exception as e:
            print(f"Error loading game: {e}")
            return None

    def apply_formatting(self, wb, sheet_name, headers):
            try:
                ws = wb[sheet_name]
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill("solid", fgColor="4F81BD")
                fill_colour = PatternFill("solid", fgColor="DCE6F1")
                thin_border = Border(
                    left=Side(style='thin'),
                    right=Side(style='thin'),
                    top=Side(style='thin'),
                    bottom=Side(style='thin')
                )

                for col_num, header_text in enumerate(headers, start=1):
                    cell = ws.cell(row=1, column=col_num, value=header_text) 
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = Alignment(horizontal="center")
        
                for col in ws.columns:
                    max_length = 0
                    column_letter = col[0].column_letter
                    for cell in col:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    ws.column_dimensions[column_letter].width = max_length + 2

                for row_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=ws.max_row,
                                                           min_col=1, max_col=ws.max_column), start=1):
                    for cell in row:
                        cell.border = thin_border
                    if row_idx > 1 and (row_idx % 2 == 0): 
                        for cell in row:
                            cell.fill = fill_colour
                    elif row_idx > 1: 
                        for cell in row:
                            cell.fill = PatternFill(fill_type=None)
                ws.freeze_panes = "A2"
            except Exception as e:
                print(f"Error applying formatting: {e}")

    def save_profile_and_match_data(self, player_profile, current_match_data):
        try:
            os.makedirs(self.excel_folder_path, exist_ok=True)
            player_name = player_profile.get('Player Name', self.name)
            full_path = os.path.join(self.excel_folder_path, f"{player_name}_profile_excel.xlsx")

            profile_data = {}
            for key, value in player_profile.items():
                if key != 'Player Name':
                    profile_data[key] = [value]
            
            profile_df = pd.DataFrame(profile_data)

            existing_matches = pd.DataFrame()
            if os.path.exists(full_path):
                try:
                    existing_matches = pd.read_excel(full_path, sheet_name="Match_History")
                except Exception:
                    existing_matches = pd.DataFrame()

            if current_match_data:
                new_match_df = pd.DataFrame([current_match_data])
                combined_matches = pd.concat([existing_matches, new_match_df], ignore_index=True)
                if "Match Number" in combined_matches.columns:
                    combined_matches.drop_duplicates(subset=["Match Number"], keep="last", inplace=True)
            else:
                combined_matches = existing_matches

            with pd.ExcelWriter(full_path, engine="openpyxl", mode="w") as writer:
                profile_df.to_excel(writer, sheet_name="Lifetime_Stats", index=False, header=True)
                combined_matches.to_excel(writer, sheet_name="Match_History", index=False, header=True)

            try:
                wb = load_workbook(full_path)
                if not profile_df.empty:
                    self.apply_formatting(wb, "Lifetime_Stats", list(profile_df.columns))
                if not combined_matches.empty:
                    self.apply_formatting(wb, "Match_History", list(combined_matches.columns))
                wb.save(full_path)
            except Exception as e:
                print(f"Warning: Could not apply formatting → {e}")

            print("Data successfully written to Excel.")

        except Exception as e:
            print(f"Error writing data to Excel file: {e}")

    def get_current_match_data(self, game_var):
        player_1st_rr = 0
        player_2nd_rr = 0
        ai_1st_rr = 0
        ai_2nd_rr = 0
        
        if game_var.get('balls_played_first_inn', 0) > 0:
            if game_var['toss_result'] == "batting":
                player_1st_rr = round((game_var['player_runs_1stinn'] * 6) / game_var['balls_played_first_inn'], 2)
            else:
                ai_1st_rr = round((game_var['ai_runs_1stinn'] * 6) / game_var['balls_played_first_inn'], 2)
                
        if game_var.get('balls_played_sec_inn', 0) > 0:
            if game_var['toss_result'] == "bowling":
                player_2nd_rr = round((game_var['player_runs_2ndinn'] * 6) / game_var['balls_played_sec_inn'], 2)
            else:
                ai_2nd_rr = round((game_var['ai_runs_2ndinn'] * 6) / game_var['balls_played_sec_inn'], 2)
        
        player_match_runs = game_var.get('player_runs_1stinn', 0) + game_var.get('player_runs_2ndinn', 0)
        player_match_balls_faced = game_var.get("balls_played_by_player", 0)
        player_match_wickets_taken = game_var.get('current_match_wickets', 0) 
        player_match_runs_conceded = game_var.get('player_runs_conceded_1stinn', 0) + game_var.get('player_runs_conceded_2ndinn', 0)
        player_match_balls_bowled = game_var.get('player_balls_bowled_1stinn', 0) + game_var.get('player_balls_bowled_2ndinn', 0)

        player_match_strike_rate = self.calculate_strike_rate(player_match_runs, player_match_balls_faced)
        player_match_economy_rate = self.calculate_economy_rate(player_match_runs_conceded, player_match_balls_bowled)

        return {
            "Match Number": game_var.get('total_matches_played', 0),
            "Player Runs 1st Innings": game_var.get('player_runs_1stinn', 0),
            "AI Runs 1st Innings": game_var.get('ai_runs_1stinn', 0),
            "Player Runs 2nd Innings": game_var.get('player_runs_2ndinn', 0),
            "AI Runs 2nd Innings": game_var.get('ai_runs_2ndinn', 0),
            "Player 1st Inn Run Rate": player_1st_rr,
            "Player 2nd Inn Run Rate": player_2nd_rr,
            "AI 1st Inn Run Rate": ai_1st_rr,
            "AI 2nd Inn Run Rate": ai_2nd_rr,
            "Player Match Strike Rate": player_match_strike_rate,
            "Player Match Economy Rate": player_match_economy_rate,
            "Player Match Wickets Taken": player_match_wickets_taken, 
            "Player Match Runs Conceded": player_match_runs_conceded,
            "Player Match Balls Bowled": player_match_balls_bowled,
            "Toss Result": game_var.get('toss_result', ""),
            "Balls Played 1st Innings": game_var.get('balls_played_first_inn', 0),
            "Balls Played 2nd Innings": game_var.get('balls_played_sec_inn', 0),
            "Difficulty": game_var.get('difficulty', 'medium'),
            "Match Result": game_var.get('match_result', 'unknown')
        }
class GamePlay:
    def __init__(self, player_name, min_choice=0, max_choice=10, score_alignment=80, difficulty = None, commentator = None):
        self.name = player_name
        self.min_choice = min_choice
        self.max_choice = max_choice
        self.score_alignment = score_alignment
        self.difficulty = difficulty
        self.commentator = commentator

    def input_num(self):
        while True:
            try:
                player_choice = int(input(f"Choose between {self.min_choice} and {self.max_choice}: "))
                if player_choice < self.min_choice or player_choice > self.max_choice:
                    print("Invalid number")
                    continue
                return player_choice
            except ValueError:
                print("Invalid number")
            except KeyboardInterrupt:
                print("\nCan't quit here")

    def get_ai_choice(self, player_prev_choice=None, ai_role=None):
        if self.difficulty == "easy":
            return random.randint(self.min_choice, self.max_choice)

        elif self.difficulty == "medium":
            choices = list(range(self.min_choice, self.max_choice + 1))
            if ai_role == "batting":
                if player_prev_choice in choices:
                    choices.remove(player_prev_choice)
            elif ai_role == "bowling":
                if player_prev_choice in choices:
                    choices += [player_prev_choice] * 2
            return random.choice(choices)

        elif self.difficulty == "hard":
            if ai_role == "bowling":
                if player_prev_choice != 0 and random.random() < 0.7:
                    return player_prev_choice
                else:
                    return random.randint(self.min_choice, self.max_choice)
            elif ai_role == "batting":
                if player_prev_choice != 0 and random.random() < 0.7:
                    avoid = [i for i in range(self.min_choice, self.max_choice + 1) if i != player_prev_choice]
                    return random.choice(avoid)
                else:
                    return random.randint(self.min_choice, self.max_choice)
        return random.randint(self.min_choice, self.max_choice)

    def calculate_run_rate(self, runs, balls_played):
        if balls_played == 0:
            return 0.0
        return round((runs * 6) / balls_played, 2)

    def calculate_required_run_rate(self, runs_needed, balls_remaining):
        if balls_remaining == 0:
            return 0.0 if runs_needed <= 0 else float('inf')
        return round((runs_needed * 6) / balls_remaining, 2)

    def display_run_rate_after_over(self, runs, balls_played, player_name="Player"):
        if balls_played > 0 and balls_played % 6 == 0:  
            run_rate = self.calculate_run_rate(runs, balls_played)
            over_number = balls_played // 6
            print(f"\n--- After Over {over_number} ---")
            print(f"{player_name} Run Rate: {run_rate} runs per over")
            print(f"Total: {runs} runs in {balls_played} balls ({over_number} overs)")
            print("=" * 35)

    def calculate_strike_rate(self, runs, balls_faced):
        if balls_faced == 0:
            return 0.0
        return round((runs / balls_faced) * 100, 2)
    
    def calculate_economy_rate(self, runs_conceded, balls_bowled):
        if balls_bowled == 0:
            return 0.0
        return round((runs_conceded / balls_bowled) * 6, 2)
    
    def check_milestones(self, current_runs, prev_runs, game_var):
        if prev_runs < 50 <= current_runs:
            game_var['half_centuries'] += 1
            if self.commentator and self.commentator.enabled:
                self.commentator.milestone_commentary(self.name, 50)
        if prev_runs < 100 <= current_runs:
            game_var['centuries'] += 1
            if self.commentator and self.commentator.enabled:
                self.commentator.milestone_commentary(self.name, 100)

    def intro(self):
        print(f"\nWelcome to AVG Hand Cricket, {self.name}!")
        print("- Prattik | XII-'A' SAP JEE".rjust(self.score_alignment))

    def match_over(self, game_var):
        while True:
            try:
                game_var['over'] = int(input("\nEnter the amount of overs: "))
                if game_var['over'] < 1:
                    print("Enter a number greater than 0")
                    continue
                return game_var['over']
            except ValueError:
                print("Please enter a valid integer")

    def toss(self, game_var):
        while True:
            player_decision = input("\nEnter odd or even: ").strip().lower()
            if player_decision in ["even", "odd"]:
                ai_decision = "odd" if player_decision == "even" else "even"
                break
            else:
                print("Invalid odd or even")

        print(f"{self.name} chose {player_decision} | AI chose {ai_decision}")        

        while True:
            try:
                player_hand = int(input(f"Enter a number between {self.min_choice} and {self.max_choice}: "))
                if self.min_choice <= player_hand <= self.max_choice:
                    break
                else:
                    print("Invalid number")
            except ValueError:
                print("Invalid number")

        ai_hand = random.randint(self.min_choice, self.max_choice)

        print(f"{self.name} chose {player_hand} | AI chose {ai_hand}")

        role_picked = player_hand + ai_hand

        if player_decision == "odd":
            if role_picked % 2 == 0:
                ai_role = random.choice(["Bat", "Bowl"])
                print(f"AI chose to {ai_role}")

                if ai_role == "Bat":
                    if self.commentator and self.commentator.enabled:
                        self.commentator.toss_commentary("AI", ai_role.lower())
                    print(f"\n{self.name} is bowling \nAI is batting")
                    game_var['toss_result'] = "bowling"
                else:
                    if self.commentator and self.commentator.enabled:
                        self.commentator.toss_commentary("AI", ai_role.lower())
                    print(f"\n{self.name} is batting \nAI is bowling")
                    game_var['toss_result'] = "batting"
            else:
                while True:
                    player_role = input("Choose to bat or bowl? ").strip().lower()
                    if player_role == "bat":
                        if self.commentator and self.commentator.enabled:
                            self.commentator.toss_commentary(self.name, player_role)
                        print(f"\n{self.name} is batting \nAI is bowling")
                        game_var['toss_result'] = "batting"
                        break
                    elif player_role == "bowl":
                        if self.commentator and self.commentator.enabled:
                            self.commentator.toss_commentary(self.name, player_role)
                        print(f"\n{self.name} is bowling \nAI is batting")
                        game_var['toss_result'] = "bowling"
                        break
                    else:
                        print("Invalid bat or bowl")
        else:
            if role_picked % 2 == 0:
                while True:
                    player_role = input("Choose to bat or bowl? ").strip().lower()

                    if player_role == "bat":
                        if self.commentator and self.commentator.enabled:
                            self.commentator.toss_commentary(self.name, player_role)
                        print(f"\n{self.name} is batting \nAI is bowling")
                        game_var['toss_result'] = "batting"
                        break
                    elif player_role == "bowl":
                        if self.commentator and self.commentator.enabled:
                            self.commentator.toss_commentary(self.name, player_role)
                        print(f"\n{self.name} is bowling \nAI is batting")
                        game_var['toss_result'] = "bowling"
                        break
                    else:
                        print("Invalid bat or bowl")
            else:
                ai_role = random.choice(["Bat", "Bowl"])
                if ai_role == "Bat":
                    if self.commentator and self.commentator.enabled:
                        self.commentator.toss_commentary("AI", ai_role.lower())
                    print(f"\n{self.name} is bowling \nAI is batting")
                    game_var['toss_result'] = "bowling"
                else:
                    if self.commentator and self.commentator.enabled:
                        self.commentator.toss_commentary("AI", ai_role.lower())
                    print(f"\n{self.name} is batting \nAI is bowling")
                    game_var['toss_result'] = "batting"

        return game_var['toss_result']

    def one_or_two(self):
        print("One or Two")
        while True:
            try:
                player_12decision = int(input("Choose between 1 and 2: "))
                if player_12decision in [1, 2]:
                    break
                else:
                    print("Invalid input")
            except ValueError:
                print("Invalid input")

        ai_12decision = random.choice([1, 2])

        print(f"{self.name} chose {player_12decision} | AI chose {ai_12decision}")
        return player_12decision, ai_12decision

    def first_in(self, game_var):
        print("\nFirst Innings:")

        if game_var['toss_result'] == "bowling":
            for ball in range(1, game_var['balls'] + 1):
                player_choice = self.input_num()
                ai_role = "bowling" if game_var['toss_result'] == "batting" else "batting"
                ai_choice = self.get_ai_choice(player_choice, ai_role)

                print(f"Ball {ball}: {self.name} chose {player_choice} | AI chose {ai_choice}")

                game_var["balls_played_first_inn"] += 1
                game_var["player_balls_bowled_1stinn"] += 1

                if player_choice == ai_choice and player_choice != 0:
                    self.commentator.wicket_commentary("AI", bowler = self.name)
                    print("First Innings Over")
                    game_var['lifetime_wickets'] += 1
                    game_var['current_match_wickets'] += 1
                    break

                if player_choice == 0 and ai_choice == 0:
                    player_12decision, ai_12decision = self.one_or_two()
                    if player_12decision == ai_12decision:
                        self.commentator.wicket_commentary("AI", bowler = self.name)
                        print(f"First Innings Over \nAI has hit {game_var['ai_runs_1stinn']} runs")
                        game_var['lifetime_wickets'] += 1
                        game_var['current_match_wickets'] += 1
                        break

                game_var['ai_runs_1stinn'] += ai_choice
                game_var['player_runs_conceded_1stinn'] += ai_choice
                if self.commentator and self.commentator.enabled:
                    self.commentator.run_commentary(ai_choice)
                print(f"Current AI runs: {game_var['ai_runs_1stinn']}".rjust(self.score_alignment))

                self.display_run_rate_after_over(
                    game_var['ai_runs_1stinn'], 
                    game_var["balls_played_first_inn"], 
                    "AI"
                )

            print(f"\nAI has hit {game_var['ai_runs_1stinn']} runs")
            final_run_rate = self.calculate_run_rate(game_var['ai_runs_1stinn'], game_var["balls_played_first_inn"])
            print(f"AI Final Run Rate: {final_run_rate} runs per over")
            print(f"\n{self.name} needs {game_var['ai_runs_1stinn'] + 1} runs to win")

        if game_var['toss_result'] == "batting":
            for ball in range(1, game_var['balls'] + 1):
                player_choice = self.input_num()
                ai_role = "bowling" if game_var['toss_result'] == "batting" else "batting"
                ai_choice = self.get_ai_choice(player_choice, ai_role)

                print(f"Ball {ball}: {self.name} chose {player_choice} | AI chose {ai_choice}")

                game_var["balls_played_first_inn"] += 1
                game_var["balls_played_by_player"] += 1

                if player_choice == ai_choice and player_choice != 0:
                    self.commentator.wicket_commentary(self.name, bowler = "AI")
                    print(f"First Innings Over \n{self.name} has hit {game_var['player_runs_1stinn']} runs")
                    break

                if player_choice == 0 and ai_choice == 0:
                    player_12decision, ai_12decision = self.one_or_two()
                    if player_12decision == ai_12decision:
                        self.commentator.wicket_commentary(self.name, bowler = "AI")
                        print(f"\nFirst Innings Over \n{self.name} has hit {game_var['player_runs_1stinn']} runs")
                        break
                    else:
                        continue

                prev_player_runs = game_var['player_runs_1stinn']            
                game_var['player_runs_1stinn'] += player_choice
                game_var['lifetime_runs'] += player_choice
                self.check_milestones(game_var['player_runs_1stinn'], prev_player_runs, game_var)

                if self.commentator and self.commentator.enabled:
                    self.commentator.run_commentary(player_choice)
                print(f"Current player runs: {game_var['player_runs_1stinn']}".rjust(self.score_alignment))

                self.display_run_rate_after_over(
                    game_var['player_runs_1stinn'], 
                    game_var["balls_played_first_inn"], 
                    self.name
                )

            final_run_rate = self.calculate_run_rate(game_var['player_runs_1stinn'], game_var["balls_played_first_inn"])
            print(f"\n{self.name} Final Run Rate: {final_run_rate} runs per over")
            print(f"\nAI needs {game_var['player_runs_1stinn'] + 1} runs to win")

    def second_in(self, game_var):
        player_choice = 0
        ai_choice = 0
        player_12decision = 0
        ai_12decision = 0

        if game_var['toss_result'] == "bowling":
            print("\nSecond Innings:")
            print(f"\n{self.name} is now batting and AI is bowling")

            for i in range(1, game_var['balls'] + 1):
                if game_var['player_runs_2ndinn'] > game_var['ai_runs_1stinn']:
                    print(f"{self.name} has achieved the target runs")
                    game_var['match_result'] = "win"
                    print("\nSecond Innings Over")
                    break

                player_choice = self.input_num()
                ai_role = "bowling" if game_var['toss_result'] == "batting" else "batting"
                ai_choice = self.get_ai_choice(player_choice, ai_role)

                print(f"Ball {i}: {self.name} chose {player_choice} | AI chose {ai_choice}")

                game_var['balls_played_sec_inn'] += 1
                game_var["balls_played_by_player"] += 1


                if player_choice == ai_choice and player_choice != 0:
                    self.commentator.wicket_commentary(self.name, bowler = "AI")
                    print(f"\nSecond Innings Over \n{self.name} has hit {game_var['player_runs_2ndinn']} runs")
                    break

                if player_choice == 0 and ai_choice == 0:
                    player_12decision, ai_12decision = self.one_or_two()
                    if player_12decision == ai_12decision:
                        self.commentator.wicket_commentary(self.name, bowler = "AI")
                        print(f"\nSecond Innings Over \n{self.name} has hit {game_var['player_runs_2ndinn']} runs")
                        break
                    else:
                        continue

                prev_player_runs = game_var['player_runs_2ndinn']
                game_var['player_runs_2ndinn'] += player_choice
                game_var['lifetime_runs'] += player_choice
                self.check_milestones(game_var['player_runs_2ndinn'], prev_player_runs, game_var)
                if self.commentator and self.commentator.enabled:
                    self.commentator.run_commentary(player_choice)
                print(f"Current player runs: {game_var['player_runs_2ndinn']}".rjust(self.score_alignment))
                if i % 6 == 0: 
                    current_run_rate = self.calculate_run_rate(game_var['player_runs_2ndinn'], game_var['balls_played_sec_inn'])
                    required_run_rate = self.calculate_required_run_rate(
                        game_var['ai_runs_1stinn'] + 1 - game_var['player_runs_2ndinn'], 
                        game_var['balls'] - game_var['balls_played_sec_inn']
                    )
                    print(f"\n--- After Over {i//6} ---")
                    print(f"Current Run Rate: {current_run_rate}")
                    print(f"Required Run Rate: {required_run_rate}")
                    print("=" * 35)

            print(f"\n{self.name} has hit {game_var['player_runs_2ndinn']} runs")

        elif game_var['toss_result'] == "batting":
            print("\nSecond Innings:")
            print(f"\n{self.name} is now bowling and AI is batting")

            for i in range(1, game_var['balls'] + 1):
                if game_var['ai_runs_2ndinn'] > game_var['player_runs_1stinn']:
                    print("AI has achieved the target runs")
                    game_var['match_result'] = "loss" 
                    print("\nSecond Innings Over")
                    break

                player_choice = self.input_num()
                ai_role = "bowling" if game_var['toss_result'] == "batting" else "batting"
                ai_choice = self.get_ai_choice(player_choice, ai_role)

                print(f"Ball {i}: {self.name} chose {player_choice} | AI chose {ai_choice}")

                game_var["balls_played_sec_inn"] += 1
                game_var["player_balls_bowled_2ndinn"] += 1

                if player_choice == ai_choice and player_choice != 0:
                    self.commentator.wicket_commentary("AI", bowler = self.name)
                    print(f"\nSecond Innings Over")
                    game_var['lifetime_wickets'] += 1
                    game_var['current_match_wickets'] += 1
                    break

                if player_choice == 0 and ai_choice == 0:
                    player_12decision, ai_12decision = self.one_or_two()
                    if player_12decision == ai_12decision:
                        self.commentator.wicket_commentary("AI", bowler = self.name)
                        print(f"\nSecond Innings Over \nAI has hit {game_var['ai_runs_2ndinn']} runs")
                        game_var['lifetime_wickets'] += 1
                        game_var['current_match_wickets'] += 1
                        break
                    else:
                        continue

                game_var['ai_runs_2ndinn'] += ai_choice
                game_var['player_runs_conceded_2ndinn'] += ai_choice
                if self.commentator and self.commentator.enabled:
                    self.commentator.run_commentary(ai_choice)
                print(f"Current AI runs: {game_var['ai_runs_2ndinn']}".rjust(self.score_alignment))
                if i % 6 == 0:  
                    current_run_rate = self.calculate_run_rate(game_var['player_runs_2ndinn'], game_var['balls_played_sec_inn'])
                    required_run_rate = self.calculate_required_run_rate(
                        game_var['player_runs_1stinn'] + 1 - game_var['ai_runs_2ndinn'], 
                        game_var['balls'] - game_var['balls_played_sec_inn']
                    )
                    print(f"\n--- After Over {i//6} ---")
                    print(f"Current Run Rate: {current_run_rate}")
                    print(f"Required Run Rate: {required_run_rate}")
                    print("=" * 35)

            print(f"\nAI has hit {game_var['ai_runs_2ndinn']} runs")

    def super_over(self, game_var):
        while True:
            print("\n*** SUPER OVER! ***")
            print("It’s a super over! Only 1 over, whoever wins - wins the match!\n")

            player_super_runs = 0
            ai_super_runs = 0

            print(f"Player is batting first in the Super Over!")
            for ball in range(1, game_var['balls'] + 1):
                player_choice = self.input_num()
                ai_choice = self.get_ai_choice(player_choice, ai_role="bowling")
                print(f"{self.name} chose {player_choice} | AI chose {ai_choice}")

                game_var["balls_played_by_player"] += 1

                if player_choice == ai_choice:
                    print("OUT! You have lost your wicket!")
                    self.commentator.wicket_commentary(self.name, bowler = "AI")
                    print(f"{self.name} has hit {player_super_runs} runs")
                    game_var['lifetime_runs'] += player_super_runs
                    break
                else:
                    player_super_runs += player_choice
                    print(f"Current player runs: {player_super_runs}".rjust(self.score_alignment))

            print(f"\nAI is batting now \nAI has to hit {player_super_runs + 1} to win")
            for ball in range(1, game_var['balls'] + 1):
                if ai_super_runs > player_super_runs:
                    break
                player_choice = self.input_num()
                ai_choice = self.get_ai_choice(player_choice, ai_role="batting")
                print(f"{self.name} chose {player_choice} | AI chose {ai_choice}")

                if player_choice == ai_choice:
                    print("OUT! AI has lost its wicket!")
                    self.commentator.wicket_commentary("AI", bowler = self.name)
                    print(f"AI has hit {ai_super_runs} runs")
                    game_var['lifetime_wickets'] += 1
                    game_var['current_match_wickets'] += 1
                else:
                    ai_super_runs += ai_choice
                    print(f"Current AI runs: {ai_super_runs}".rjust(self.score_alignment))

            print("\nSuper Over Results:")
            print(f"Your runs: {player_super_runs} | AI runs: {ai_super_runs}")

            if player_super_runs > ai_super_runs:
                print("You win the Super Over!")
                game_var['match_result'] = "win" 
                game_var['total_wins'] += 1
                game_var['match_result'] = "win"
                break
            elif ai_super_runs > player_super_runs:
                print("AI wins the Super Over")
                game_var['match_result'] = "loss" 
                game_var['total_losses'] += 1
                game_var['match_result'] = "loss"
                break
            else:
                print("Super Over is also a tie! Another super over will be played!")
class DisplayManager:
    def print_match_summary(self, match_summary):
        print("---------- Match Summary ----------")
        for inning, stats in match_summary.items():
            print(f"{inning}:")
            for key, value in stats.items():
                if key == "run_rate":
                    print(f"Run rate: {value} runs per over")
                else:
                    score_name = key.replace("_", " ").capitalize()
                    print(f"{score_name}: {value}")
            print()
        print("-----------------------------------")

    def print_player_profile(self, profile):
        print("------- Player Profile -------")
        for key, value in profile.items():
            score_name = key.replace("_", " ").capitalize()
            print(f"{score_name}: {value}")
        print("-----------------------------")
class GameManager:
    global game_var

    def __init__(self, gameplay_instance, display_instance, db_handler, manager, player_name):
        self.gameplay = gameplay_instance
        self.display = display_instance
        self.db_handler = db_handler
        self.manager = manager
        self.name = player_name

    def result(self, game_var):
        summary = game_var['match_summary']
        if game_var['toss_result'] == "bowling":
            ai_run_rate = self.gameplay.calculate_run_rate(
                game_var['ai_runs_1stinn'], 
                game_var['balls_played_first_inn']
            )
            player_run_rate = self.gameplay.calculate_run_rate(
                game_var['player_runs_2ndinn'], 
                game_var['balls_played_sec_inn']
            )
            summary['First Innings'] = {
                "ai_runs": game_var['ai_runs_1stinn'],
                "balls_played": game_var['balls_played_first_inn'],
                "run_rate": ai_run_rate
            }
            summary['Second Innings'] = {
                "player_runs": game_var['player_runs_2ndinn'],
                "balls_played": game_var['balls_played_sec_inn'],
                "run_rate": player_run_rate
            }

            total_runs = game_var['ai_runs_1stinn'] + game_var['player_runs_2ndinn']
            total_balls = game_var['balls_played_first_inn'] + game_var['balls_played_sec_inn']
            match_avg_run_rate = self.gameplay.calculate_run_rate(total_runs, total_balls)
            
            player_match_runs = game_var.get('player_runs_1stinn', 0) + game_var.get('player_runs_2ndinn', 0)
            player_match_balls_faced = game_var.get("balls_played_by_player", 0)
            player_match_runs_conceded = game_var.get('player_runs_conceded_1stinn', 0) + game_var.get('player_runs_conceded_2ndinn', 0)
            player_match_balls_bowled = game_var.get('player_balls_bowled_1stinn', 0) + game_var.get('player_balls_bowled_2ndinn', 0)
            player_match_strike_rate = self.gameplay.calculate_strike_rate(player_match_runs, player_match_balls_faced)
            player_match_economy_rate = self.gameplay.calculate_economy_rate(player_match_runs_conceded, player_match_balls_bowled)


            summary['Match Statistics'] = {
                "average_run_rate": match_avg_run_rate,
                "total_runs_scored": total_runs,
                "total_balls_played": total_balls,
                "Player Match Strike Rate": player_match_strike_rate,
                "Player Match Economy Rate": player_match_economy_rate,
            }

            self.display.print_match_summary(summary)
            if game_var['ai_runs_1stinn'] > game_var['player_runs_2ndinn']:
                print("AI has won the game. You have lost.")
                game_var['total_losses'] += 1
                game_var['match_result'] = "loss"

            elif game_var['ai_runs_1stinn'] < game_var['player_runs_2ndinn']:
                print("You have won the game. AI has lost.")
                game_var['total_wins'] += 1
                game_var['match_result'] = "win"

            else:
                print("It's a tie!")
                game_var['total_draws'] += 1
                self.gameplay.super_over(game_var)

            game_var['lifetime_balls_faced'] += player_match_balls_faced
            game_var['lifetime_balls_bowled'] += player_match_balls_bowled
            game_var['lifetime_runs_conceded'] += player_match_runs_conceded

            current_match_data = self.manager.get_current_match_data(game_var)
            self.db_handler.save_match_data(game_var, self.name, player_match_runs_conceded, player_match_balls_bowled, game_var['current_match_wickets'])
            self.handle_profile_display_and_save(game_var, current_match_data)

        elif game_var['toss_result'] == "batting":
            ai_run_rate = self.gameplay.calculate_run_rate(
                game_var['ai_runs_2ndinn'], 
                game_var['balls_played_sec_inn']
            )
            player_run_rate = self.gameplay.calculate_run_rate(
                game_var['player_runs_1stinn'], 
                game_var['balls_played_first_inn']
            )
            summary['First Innings'] = {
                "player_runs": game_var['player_runs_1stinn'],
                "balls_played": game_var['balls_played_first_inn'],
                "run_rate": player_run_rate
            }
            summary['Second Innings'] = {
                "ai_runs": game_var['ai_runs_2ndinn'],
                "balls_played": game_var['balls_played_sec_inn'],
                "run_rate": ai_run_rate
            }

            total_runs = game_var['player_runs_1stinn'] + game_var['ai_runs_2ndinn']
            total_balls = game_var['balls_played_first_inn'] + game_var['balls_played_sec_inn']
            match_avg_run_rate = self.gameplay.calculate_run_rate(total_runs, total_balls)
            
            player_match_runs = game_var.get('player_runs_1stinn', 0) + game_var.get('player_runs_2ndinn', 0)
            player_match_balls_faced = game_var.get("balls_played_by_player", 0)
            player_match_runs_conceded = game_var.get('player_runs_conceded_1stinn', 0) + game_var.get('player_runs_conceded_2ndinn', 0)
            player_match_balls_bowled = game_var.get('player_balls_bowled_1stinn', 0) + game_var.get('player_balls_bowled_2ndinn', 0)
            player_match_strike_rate = self.gameplay.calculate_strike_rate(player_match_runs, player_match_balls_faced)
            player_match_economy_rate = self.gameplay.calculate_economy_rate(player_match_runs_conceded, player_match_balls_bowled)

            summary['Match Statistics'] = {
                "average_run_rate": match_avg_run_rate,
                "total_runs_scored": total_runs,
                "total_balls_played": total_balls,
                "Player Match Strike Rate": player_match_strike_rate,
                "Player Match Economy Rate": player_match_economy_rate,
            }

            self.display.print_match_summary(summary)
            if game_var['ai_runs_2ndinn'] > game_var['player_runs_1stinn']:
                print("AI has won the game. You have lost.")
                game_var['total_losses'] += 1
                game_var['match_result'] = "loss"

            elif game_var['ai_runs_2ndinn'] < game_var['player_runs_1stinn']:
                print("You have won the game. AI has lost.")
                game_var['total_wins'] += 1
                game_var['match_result'] = "win"
                
            else:
                print("It's a tie!")
                game_var['total_draws'] += 1
                self.gameplay.super_over(game_var)

            game_var['lifetime_balls_faced'] += player_match_balls_faced
            game_var['lifetime_balls_bowled'] += player_match_balls_bowled
            game_var['lifetime_runs_conceded'] += player_match_runs_conceded

            current_match_data = self.manager.get_current_match_data(game_var)
            self.db_handler.save_match_data(game_var, self.name, player_match_runs_conceded, player_match_balls_bowled, game_var['current_match_wickets'])
            self.handle_profile_display_and_save(game_var, current_match_data)

        else:
            print("Error: toss_result must be either 'bowling' or 'batting'.")

    def reset_game(self, game_var):
        game_var['over'] = 0
        game_var['player_runs_1stinn'] = 0
        game_var['ai_runs_1stinn'] = 0
        game_var['player_runs_2ndinn'] = 0
        game_var['ai_runs_2ndinn'] = 0
        game_var['toss_result'] = ""
        game_var['match_summary'] = {}
        game_var['balls_played_first_inn'] = 0
        game_var['balls_played_sec_inn'] = 0
        game_var['current_match_wickets'] = 0
        game_var['balls_played_by_player'] = 0
        game_var['player_balls_bowled_1stinn'] = 0
        game_var['player_balls_bowled_2ndinn'] = 0
        game_var['player_runs_conceded_1stinn'] = 0
        game_var['player_runs_conceded_2ndinn'] = 0
        game_var['match_result'] = ""

    def get_choice(self):
        while True:
            try:
                print("\n--- Main Menu ---")
                print("Type tutorial to view the tutorial.")
                print("Type play to play a match. \nType quit to quit. \nType profile to view the player profile.")
                print("Type save to save current game state.")
                print("Type load to load previous game state.")
                print("Type leaderboard to view global stats.")
                print("Type switch to switch player account.")
                print("Type settings to change commentary or difficulty.")
                choice = input(": ").strip().lower()
                if choice in ("tutorial","play", "quit", "profile", "save", "load", "leaderboard", "switch", "settings"):
                    return choice
                print("Invalid input")
            except KeyboardInterrupt:
                print("\nGame was interrupted, type no to exit properly")
                continue

    def handle_profile_display_and_save(self, game_var, current_match_data=None):
        if game_var['total_matches_played'] > 0:
            game_var['average_runs_per_match'] = (
                game_var['lifetime_runs'] / game_var['total_matches_played']
            )

        lifetime_strike_rate = self.gameplay.calculate_strike_rate(
            game_var['lifetime_runs'],
            game_var['lifetime_balls_faced']
        )

        lifetime_economy_rate = self.gameplay.calculate_economy_rate(
            game_var['lifetime_runs_conceded'],
            game_var['lifetime_balls_bowled']
        )

        lifetime_run_rate = self.gameplay.calculate_run_rate(
            game_var['lifetime_runs'],
            game_var['lifetime_balls_faced']
        )

        game_var['player_profile'] = {
            "Lifetime runs": game_var['lifetime_runs'],
            "Lifetime wickets": game_var['lifetime_wickets'],
            "Total Matches Played": game_var['total_matches_played'],
            "Total Wins": game_var['total_wins'],
            "Total Losses": game_var['total_losses'],
            "Total Draws": game_var['total_draws'],
            "Average Runs per Match": game_var['average_runs_per_match'],
            "Lifetime Balls Faced": game_var['lifetime_balls_faced'],
            "Lifetime Balls Bowled": game_var['lifetime_balls_bowled'],
            "Lifetime Runs Conceded": game_var['lifetime_runs_conceded'],
            "Lifetime Run Rate": lifetime_run_rate,
            "Lifetime Strike Rate": lifetime_strike_rate,
            "Lifetime Economy Rate": lifetime_economy_rate,
            "Centuries": game_var['centuries'],
            "Half Centuries": game_var['half_centuries']
        }
        self.display.print_player_profile(game_var['player_profile'])
        pw = self.db_handler.get_password(self.name)
        self.db_handler.save_profile(game_var['player_profile'], self.name, pw)

        if current_match_data:
            self.manager.save_profile_and_match_data(game_var['player_profile'], current_match_data)

    def show_settings_menu(self, game_var):
        while True:
            print("\n--- Settings Menu ---")
            print("1. Toggle Commentary")
            print("2. Change Difficulty")
            print("3. Change player name")
            print("4. Change password")
            print("5. Go Back")
            choice = input("Enter choice (1/2/3/4/5): ").strip()

            if choice == "1":
                self.toggle_commentary()
            elif choice == "2":
                self.change_difficulty(game_var)
            elif choice == "3":
                self.change_player_name()
            elif choice == "4":
                self.change_password()
            elif choice == "5":
                break
            else:
                print("Invalid choice. Please select 1, 2, 3, 4, or 5.")

    def toggle_commentary(self):
        current = self.gameplay.commentator.enabled
        self.gameplay.commentator.enabled = not current
        game_var["commentary_enabled"] = self.gameplay.commentator.enabled
        status = "enabled" if self.gameplay.commentator.enabled else "disabled"
        print(f"Commentary is now {status}.")

    def change_difficulty(self, game_var):
        while True:
            difficulty = input("Choose difficulty: easy / medium / hard: ").strip().lower()
            if difficulty in ("easy", "medium", "hard"):
                game_var["difficulty"] = difficulty
                self.gameplay.difficulty = difficulty
                print(f"Difficulty set to {difficulty}.")
                break
            else:
                print("Invalid choice. Try again.")

    def change_player_name(self):
        global name
        db_handler = self.db_handler
        old_name = self.name

        new_name = input("Enter new player name (max 30 characters): ").strip().title()
        if not new_name.replace(" ", "").isalpha():
            print("Invalid name. Only letters and spaces allowed.")
            return
        if len(new_name) == 0 or len(new_name) > 30:
            print("Name must be 1-30 characters.")
            return
        if new_name == old_name:
            print("New name must be different from the current name.")
            return
        if db_handler.player_exists(new_name):
            print("This player name already exists. Please choose another.")
            return

        old_pass = pwinput.pwinput("Enter your current password for confirmation: ").strip()
        if old_pass != db_handler.get_password(old_name):
            print("Incorrect password. Name not changed.")
            return

        db = db_handler.get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE player_profile SET name = %s WHERE name = %s", (new_name, old_name))
        cursor.execute("UPDATE match_data SET player_name = %s WHERE player_name = %s", (new_name, old_name))
        db.commit()
        cursor.close()

        old_json_file = f"{self.manager.json_folder_path}/{old_name}_game_save.json"
        new_json_file = f"{self.manager.json_folder_path}/{new_name}_game_save.json"
    
        old_excel_file = f"{self.manager.excel_folder_path}/{old_name}_profile_excel.xlsx"
        new_excel_file = f"{self.manager.excel_folder_path}/{new_name}_profile_excel.xlsx"
    
        files_renamed = []

        try:
            if os.path.exists(old_json_file):
                os.rename(old_json_file, new_json_file)
                files_renamed.append("game save")
        except Exception as e:
            print(f"Warning: Could not rename JSON save file: {e}")
    
        try:
            if os.path.exists(old_excel_file):
                os.rename(old_excel_file, new_excel_file)
                files_renamed.append("Excel profile")
        except Exception as e:
            print(f"Warning: Could not rename Excel file: {e}")

        print(f"Name changed from '{old_name}' to '{new_name}' successfully.")
        if files_renamed:
            print(f"Renamed save files: {', '.join(files_renamed)}")

        self.manager.name = new_name
        self.name = new_name
        name = new_name

    def change_password(self):
        db_handler = self.db_handler
        name = self.name

        old_pass = pwinput.pwinput("Enter your current password: ").strip()
        if old_pass != db_handler.get_password(name):
            print("Incorrect password. Password not changed.")
            return

        while True:
            new_pass = pwinput.pwinput("Enter new password: ").strip()
            if len(new_pass) < 3:
                print("Password must be at least 3 characters long.")
                continue
            confirm = pwinput.pwinput("Confirm new password: ").strip()
            if new_pass != confirm:
                print("Passwords do not match. Try again.")
            else:
                db_handler.update_password(name, new_pass)
                print("Password updated successfully.")
                break

    def handle_save_game_and_profile(self, game_var):
        self.manager.save_game_to_file(game_var)
        if game_var['total_matches_played'] > 0:
            game_var['average_runs_per_match'] = (
                game_var['lifetime_runs'] / game_var['total_matches_played']
            )
        profile = {
            "Player Name": self.name,
            "Lifetime runs": game_var['lifetime_runs'],
            "Lifetime wickets": game_var['lifetime_wickets'],
            "Total Matches Played": game_var['total_matches_played'],
            "Total Wins": game_var['total_wins'],
            "Total Losses": game_var['total_losses'],
            "Total Draws": game_var['total_draws'],
            "Average Runs per Match": game_var['average_runs_per_match'],
            "Lifetime Balls Faced": game_var['lifetime_balls_faced'],
            "Lifetime Balls Bowled": game_var['lifetime_balls_bowled'],
            "Lifetime Runs Conceded": game_var['lifetime_runs_conceded'],
            "Centuries": game_var['centuries'],
            "Half Centuries": game_var['half_centuries']
        }

        current_match_data = self.manager.get_current_match_data(game_var)
        self.manager.save_profile_and_match_data(profile, current_match_data)
class Commentator:
    def __init__(self, enabled=True):
        self.enabled = enabled

    def say(self, messages):
        if self.enabled:
            print("\nCommentator:", random.choice(messages))

    def run_commentary(self, runs):
        if runs == 0:
            self.say(["That's a dot ball!", "No run scored.", "Good ball, no run."])
        elif runs == 1:
            self.say(["Just a single.", "Quick single taken.", "Keeps the scoreboard ticking."])
        elif runs == 2:
            self.say(["Two runs added! Great work they're putting it!", "Great running between the wickets."])
        elif runs == 3:
            self.say(["Three runs! That's rare.", "Excellent placement and running."])
        elif runs == 4:
            self.say(["That's a FOUR!", "Cracking shot through the gap!", "That races to the boundary!"])
        elif runs == 6:
            self.say(["SIX! What a hit!", "That's out of the park!", "Massive hit!"])
        elif runs == 7:
            self.say(["Seven runs! great thinking here.", "They chose for a seven this time.", "They're looking far ahead"])
        elif runs == 8:
            self.say(["Eight! Great decision.", "An Eight! He's confident.", "He just smashed it!"])
        elif runs == 9:
            self.say(["Nine runs! they know what they're doing here.", "Makes me wanna sing a song right now.", "Thats it! They can go home happy now!"])
        elif runs == 10:
            self.say(["A TEN!, What a shot!", "That's out of the planet!","Holy mother of GOD I'm SCREAMINGGGGG"])

    def wicket_commentary(self, out_batsman, bowler = "AI"):
        self.say([
            f"{out_batsman} is OUT! Bowled by {bowler}!",
            f"{out_batsman} departs! What a delivery from {bowler}!",
            f"What a catch! {out_batsman} is gone, bowled by {bowler}!",
            f"{out_batsman} has been dismissed! {bowler} takes the wicket!",
            f"{out_batsman} is back to the pavilion! {bowler} strikes",
            f"{out_batsman} is out! {bowler} with a brilliant delivery!",
            f"{out_batsman} has been sent packing! {bowler} gets the wicket!",
            f"{out_batsman} is gone! {bowler} with a fantastic ball!",
            f"{out_batsman} is out! {bowler} takes the wicket with a superb delivery!",
            f"What a day he must be having right now! Superb bowling from {bowler}!",
            f"He must be feeling on top of the world right now! {bowler} gets the wicket!",
            f"He must've missed his morning grace! {out_batsman} is out!",
            f"{out_batsman} is out! {bowler} bowls a peach of a delivery!",
            f"{out_batsman} is out! {bowler} with a brilliant delivery!",
            f"Wicket! {bowler} gets rid of {out_batsman}!"
        ])

    def toss_commentary(self, winner, decision):
        self.say([
            f"{winner} wins the toss and chooses to {decision}, Dunno what they're thinking.",
            f"The toss is won by {winner}, they opt to {decision}, Makes sense at this time of the day.",
            f"{winner} decides to {decision} after winning the toss, some quality decision making here."
        ])

    def milestone_commentary(self, player_name, milestone):
        if self.enabled:
            if milestone == 50:
                self.say([
                    f"That's a brilliant fifty for {player_name}!",
                    f"{player_name} reaches his half-century with style!",
                    f"Fifty up for {player_name}! What an innings this is turning out to be.",
                    f"{player_name} brings up his fifty! A well-deserved milestone!",
                    f"Half-century for {player_name}! He is looking in great touch!",
                    f"{player_name} has reached his fifty! A fantastic effort!",
                    f"Fifty! {player_name} has played a superb innings so far!",
                    f"What a partnership this is turning out to be! {player_name} has reached his fifty!",
                    f"He lifts his bat up!!! What a moment for {player_name}!",
                ])
            elif milestone == 100:
                self.say([
                    f"A magnificent century for {player_name}! Take a bow!",
                    f"And he lifts his bat up! Imagine how he must be feeling right now!",
                    f"This is the moment he has been waiting for! God Bless Him!",
                    f"{player_name} has shown the world yet again why he is a class player!",
                    f"{player_name} brings up his hundred! An outstanding display of batting!",
                    f"Hundred! {player_name} has reached the magical three-figure mark!",
                ])
class LeaderboardManager:
    def __init__(self, db):
        self.db = db  

    def show_menu(self):
        while True:
            print("\n--- LEADERBOARD MENU ---")
            print("0. Leaderboard info")
            print("1. Runs Leaderboard")
            print("2. Wickets Leaderboard")
            print("3. Balls Played Leaderboard")
            print("4. Most Active Players (Matches Played)")
            print("5. Highest Scores")
            print("6. Win Rate Leaderboard")
            print("7. All-Rounders Leaderboard")
            print("8. Lifetime Run Rate Leaderboard")
            print("9. Lifetime Strike Rate Leaderboard") 
            print("10. Lifetime Economy Rate Leaderboard") 
            print("11. Half Centuries Leaderboard")
            print("12. Centuries Leaderboard") 
            print("13. Back to Main Menu")

            choice = input("Enter your choice: ").strip()

            options = {
                "0": self.leaderboard_info,
                "1": self.show_runs,
                "2": self.show_wickets,
                "3": self.show_balls_played,
                "4": self.show_most_active,
                "5": self.show_high_scores,
                "6": self.show_win_rate,
                "7": self.show_all_rounders,
                "8": self.show_lifetime_run_rate,
                "9": self.show_lifetime_strike_rate, 
                "10": self.show_lifetime_economy_rate, 
                "11": self.show_half_centuries,
                "12": self.show_centuries
            }

            if choice in options:
                options[choice]()
            elif choice == "13":
                break
            else:
                print("Invalid choice! Try again.")

    def leaderboard_info(self):
        print("\n--- Leaderboard Info ---")
        print("This leaderboard shows the top 10 players based on various statistics.")
        print("1. Runs Leaderboard: Total runs scored by each player.")
        print("2. Wickets Leaderboard: Total wickets taken by each player.")
        print("3. Balls Played Leaderboard: Total balls faced by each player.")
        print("4. Most Active Players: Players with the most matches played.")
        print("5. Highest Scores: Highest individual scores by players.")
        print("6. Lifetime Run Rate Leaderboard: Average runs per over for players.")
        print("7. Win Rate Leaderboard: Percentage of matches won by each player.")
        print("8. All-Rounders Leaderboard: Combined score of runs and wickets for all-rounder performance.")
        print("9. Lifetime Strike Rate Leaderboard: Runs scored per 100 balls faced.") 
        print("10. Lifetime Economy Rate Leaderboard: Runs conceded per over bowled.") 
        print("11. Centuries Leaderboard: Total centuries scored by each player.") 
        print("12. Half Centuries Leaderboard: Total half-centuries scored by each player.")

    def show_runs(self):
        lbcursor = self.db.get_db()
        cursor = lbcursor.cursor()
        cursor.execute("""
            SELECT player_name, SUM(runs) as total_runs
            FROM match_data
            GROUP BY player_name
            ORDER BY total_runs DESC
            LIMIT 10
        """)
        self._print_results("Runs", cursor.fetchall())
        cursor.close()

    def show_wickets(self):
        lbcursor = self.db.get_db()
        cursor = lbcursor.cursor()
        cursor.execute("""
            SELECT player_name, SUM(wickets) as total_wickets
            FROM match_data
            GROUP BY player_name
            ORDER BY total_wickets DESC
            LIMIT 10
        """)
        self._print_results("Wickets", cursor.fetchall())
        cursor.close()

    def show_balls_played(self):
        lbcursor = self.db.get_db()
        cursor = lbcursor.cursor()
        cursor.execute("""
            SELECT player_name, SUM(balls_faced) as total_balls
            FROM match_data
            GROUP BY player_name
            ORDER BY total_balls DESC
            LIMIT 10
        """)
        self._print_results("Balls Played", cursor.fetchall())
        cursor.close()

    def show_most_active(self):
        lbcursor = self.db.get_db()
        cursor = lbcursor.cursor()
        cursor.execute("""
            SELECT player_name, COUNT(*) as matches_played
            FROM match_data
            GROUP BY player_name
            ORDER BY matches_played DESC
            LIMIT 10
        """)
        self._print_results("Matches Played", cursor.fetchall())
        cursor.close()

    def show_high_scores(self):
        lbcursor = self.db.get_db()
        cursor = lbcursor.cursor()
        cursor.execute("""
            SELECT player_name, MAX(runs) as highest_score
            FROM match_data
            GROUP BY player_name
            ORDER BY highest_score DESC
            LIMIT 10
        """)
        self._print_results("Highest Score", cursor.fetchall())
        cursor.close()

    def show_win_rate(self):
        lbcursor = self.db.get_db()
        cursor = lbcursor.cursor()
        cursor.execute("""
            SELECT player_name,
                   SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins,
                   COUNT(*) AS matches,
                   ROUND(SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) / COUNT(*) * 100, 2) AS win_rate
            FROM match_data
            GROUP BY player_name
            HAVING matches > 0
            ORDER BY win_rate DESC
            LIMIT 10
        """)

        results = cursor.fetchall()

        print(f"\n--- Win Rate Leaderboard ---")
        print(f"{'Rank':<6}{'Player':<15}{'Win Rate':<12}{'Record (W/M)':<15}")
        print("-" * 50)
    
        for i, row in enumerate(results, 1):
            player_name, wins, matches, win_rate = row
            print(f"{i:<6}{player_name.upper():<15}{win_rate}%{'':<7}{wins}/{matches}{'':10}")
    
        cursor.close()

    def show_all_rounders(self):
        lbcursor = self.db.get_db()
        cursor = lbcursor.cursor()
        cursor.execute("""
            SELECT player_name,
                   SUM(runs) + SUM(wickets * 20) as all_rounder_score
            FROM match_data
            GROUP BY player_name
            ORDER BY all_rounder_score DESC
            LIMIT 10
        """)
        self._print_results("All-Rounder Score", cursor.fetchall())
        cursor.close()

    def show_lifetime_run_rate(self):
        lbcursor = self.db.get_db()
        cursor = lbcursor.cursor()
        cursor.execute("""
            SELECT name,
                    lifetime_runs,
                    lifetime_balls_faced,
                    CASE 
                       WHEN lifetime_balls_faced > 0 
                       THEN ROUND((lifetime_runs * 6.0) / lifetime_balls_faced, 2)
                       ELSE 0.0
                    END as lifetime_run_rate
            FROM player_profile
            WHERE lifetime_balls_faced > 0
            ORDER BY lifetime_run_rate DESC
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        print(f"\n--- Lifetime Run Rate Leaderboard ---")
        print(f"{'Rank':<6}{'Player':<15}{'Run Rate':<12}{'Runs/Balls':<15}")
        print("-" * 50)
        
        for i, row in enumerate(results, 1):
            player_name, lifetime_runs, lifetime_balls_faced, lifetime_run_rate = row
            print(f"{i:<6}{player_name.upper():<15}{lifetime_run_rate:<12}{lifetime_runs}/{lifetime_balls_faced}")
        
        cursor.close()

    def show_lifetime_strike_rate(self):
        lbcursor = self.db.get_db()
        cursor = lbcursor.cursor()
        cursor.execute("""
            SELECT name,
                    lifetime_runs,
                    lifetime_balls_faced,
                    CASE
                       WHEN lifetime_balls_faced > 0
                       THEN ROUND((lifetime_runs * 100.0) / lifetime_balls_faced, 2)
                       ELSE 0.0
                   END as lifetime_strike_rate
            FROM player_profile
            WHERE lifetime_balls_faced > 0
            ORDER BY lifetime_strike_rate DESC
            LIMIT 10
        """)
        results = cursor.fetchall()
        print(f"\n--- Lifetime Strike Rate Leaderboard ---")
        print(f"{'Rank':<6}{'Player':<15}{'SR':<10}{'Runs/Balls':<15}")
        print("-" * 50)

        for i, row in enumerate(results, 1):
            player_name, lifetime_runs, lifetime_balls_faced, strike_rate = row
            print(f"{i:<6}{player_name.upper():<15}{strike_rate:<10}{lifetime_runs}/{lifetime_balls_faced}")

        cursor.close()

    def show_lifetime_economy_rate(self):
        lbcursor = self.db.get_db()
        cursor = lbcursor.cursor()
        cursor.execute("""
                        SELECT name,
                        lifetime_runs_conceded,
                        lifetime_balls_bowled,
                        CASE
                        WHEN lifetime_balls_bowled > 0
                        THEN ROUND(lifetime_runs_conceded * 6.0 / lifetime_balls_bowled, 2)
                        ELSE 0.0
                    END as lifetime_economy_rate
                FROM player_profile
                WHERE lifetime_balls_bowled > 0
                ORDER BY lifetime_economy_rate ASC 
                LIMIT 10
            """)
        results = cursor.fetchall()
        print(f"\n--- Lifetime Economy Rate Leaderboard ---")
        print(f"{'Rank':<6}{'Player':<15}{'ER':<10}{'Runs Conceded/Balls Bowled':<30}")
        print("-" * 60)

        for i, row in enumerate(results, 1):
            player_name, lifetime_runs_conceded, lifetime_balls_bowled, lifetime_economy_rate = row
            print(f"{i:<6}{player_name.upper():<15}{lifetime_economy_rate:<10}{lifetime_runs_conceded}/{lifetime_balls_bowled}")

        cursor.close()

    def show_half_centuries(self):
        lbcursor = self.db.get_db()
        cursor = lbcursor.cursor()
        cursor.execute("""
            SELECT name, SUM(half_centuries) AS total_half_centuries
            FROM player_profile
            GROUP BY name
            ORDER BY total_half_centuries DESC
            LIMIT 10
        """)
        self._print_results("Half Centuries", cursor.fetchall())

        cursor.close()

    def show_centuries(self):
        lbcursor = self.db.get_db()
        cursor = lbcursor.cursor()
        cursor.execute("""
            SELECT name, SUM(centuries) AS total_centuries
            FROM player_profile
            GROUP BY name
            ORDER BY total_centuries DESC
            LIMIT 10
        """)
        self._print_results("Centuries", cursor.fetchall())

        cursor.close()

    def _print_results(self, title, results):
        print(f"\n--- {title} Leaderboard ---")
        print(f"{'Rank':<6}{'Player':<15}{title:<20}")
        for i, row in enumerate(results, 1):
            print(f"{i:<6}{row[0].upper():<15}{row[1]:<20}")
def ask_commentary_setting():
    while True:
        try:
            choice = input("Do you want commentary? (yes/no): ").strip().lower()
            if choice == "yes":
                return True
            elif choice == "no":
                return False
            else:
                print("Invalid input! Please enter yes or no.")
        except KeyboardInterrupt:
            print("Game interrupted! try again")
def ask_difficulty_setting():
    while True:
        try:
            difficulty = input("Choose difficulty: easy / medium / hard: ").strip().lower()
            if difficulty in ("easy", "medium", "hard"):
                print(f"Difficulty set to {difficulty}.")
                return difficulty
            else:
                print("Invalid choice. Try again.")
        except KeyboardInterrupt:
            print("Game interrupted! try again")
def login_menu(db_handler, name):
    while True:
        print("\n--- Login Menu ---")
        print("1. Start Game")
        print("2. Change Password")
        print("3. Logout")
        choice = input("Choose: ").strip()
        
        if choice == "1":
            return True
        elif choice == "2":
            old_pass = pwinput.pwinput("Enter current password: ").strip()
            if old_pass == db_handler.get_password(name):
                new_pass = pwinput.pwinput("Enter new password: ").strip()
                confirm = pwinput.pwinput("Confirm new password: ").strip()
                if new_pass == confirm:
                    db_handler.update_password(name, new_pass)
                    print("Password updated successfully.")
                else:
                    print("Passwords do not match.")
            else:
                print("Incorrect current password.")
        elif choice == "3":
            return False
        else:
            print("Invalid choice.")
def player_login(db_handler):
    global game_var
    while True:
        try:
            name = input("Enter your name (max 30 characters): ").strip().title()
            if not name.replace(" ", "").isalpha():
                print("Invalid name. Only letters and spaces allowed.")
                continue
            if len(name) == 0:
                print("Name cannot be empty.")
                continue
            if len(name) > 30:
                print(f"Name too long! ({len(name)}/30 characters)")
                continue

            if db_handler.player_exists(name):
                print(f"Welcome back, {name}!")
                stored_password = db_handler.get_password(name)
                authenticated = False
                print("You have 3 attempts to enter your password.")

                for attempt in range(3):
                    entered_pass = pwinput.pwinput("\nEnter your password: ").strip()
                    if entered_pass == stored_password:
                        authenticated = True
                        break
                    else:
                        print("Incorrect password, Try again.")
                if not authenticated:
                    print("Too many failed attempts. Exiting login.")
                    return None
                
                print(f"Logging in as {name}...")
                time.sleep(2)
                reset = input("Do you want to reset your stats? (yes/no): ").strip().lower()
                if reset == "yes":
                    print("Resetting profile and match history...")
                    time.sleep(2)
                    profile = {
                        "Lifetime runs": 0,
                        "Lifetime wickets": 0,
                        "Total Matches Played": 0,
                        "Total Wins": 0,
                        "Total Losses": 0,
                        "Total Draws": 0,
                        "Average Runs per Match": 0,
                        "Lifetime Balls Faced": 0,
                        "Lifetime Balls Bowled": 0,
                        "Lifetime Runs Conceded": 0,
                        "Centuries": 0,
                        "Half Centuries": 0,
                    }
                    db_handler.save_profile(profile, name, stored_password)
                    
                    db = db_handler.get_db()
                    cursor = db.cursor()
                    cursor.execute("DELETE FROM match_data WHERE player_name = %s", (name,))
                    db.commit()
                    cursor.close()
                    
                    print("Profile and match history reset.")
                return name
            else:
                print(f"Profile for {name} does not exist. Creating a new profile...")
                time.sleep(2)
                while True:
                    password = pwinput.pwinput("Create a password: ").strip()
                    if len(password) < 3:
                        print("Password must be at least 3 characters long.")
                        continue
                    confirm = pwinput.pwinput("Confirm password: ").strip()
                    if password != confirm:
                        print("Passwords do not match. Try again.")
                    else:
                        break
                print(f"Creating new profile for {name}...")
                time.sleep(3)
                print(f"Profile successfully created for {name}")
                profile = {
                    "Lifetime runs": 0,
                    "Lifetime wickets": 0,
                    "Total Matches Played": 0,
                    "Total Wins": 0,
                    "Total Losses": 0,
                    "Total Draws": 0,
                    "Average Runs per Match": 0,
                    "Lifetime Balls Faced": 0,
                    "Lifetime Balls Bowled": 0,
                    "Lifetime Runs Conceded": 0,
                    "Centuries": 0,
                    "Half Centuries": 0,
                }
                db_handler.save_profile(profile, name, password)

            return name
        except KeyboardInterrupt:
            print("Login interrupted, try again.")
def main(game_manager):
    global game_var, manager, name, gameplay, commentator, display
    while True:
        choice = game_manager.get_choice()

        if choice == "tutorial":
            print("\nTutorial: \nChoose Odd or even:")
            print("  :You will be playing against an AI opponent")
            print("  :AI will choose the opposite of what you will choose \n  :If the sum of the numbers corresponds to what you choose then you'll get the opportunity to choose to bat or bowl")
            print("  :There will be two innings from bat to bowl or bowl to bat")
            print("  :Using the same numbers will drop a wicket \n  :Each number will add to your total runs")
            print("  :At the end, who has the highest amount of runs wins!")
            print("  :Note that in case both Player and AI choose 0, it will lead to the 1 or 2 rule-which means that only 1 or 2 is allowed - but they don't count as runs!")
            print("  :In case of tie, a super over will occur! super over means only 1 over with just 6 balls!")
            print("\nHave a great time playing!!!")

        elif choice == "play":
            game_var['total_matches_played'] += 1
            game_manager.reset_game(game_var)
            toss_result = gameplay.toss(game_var)
            over = gameplay.match_over(game_var)
            game_var['balls'] = game_var['over'] * balls_per_over
            gameplay.first_in(game_var)
            gameplay.second_in(game_var)
            game_manager.result(game_var)

        elif choice == "quit":
            print("Thank you for playing")
            db_handler.close_db()
            break

        elif choice == "save":
            print("Saving game state...")
            time.sleep(3)
            game_manager.handle_save_game_and_profile(game_var)

        elif choice == "load":
            print("Loading save game state...")
            time.sleep(3)
            loaded_game = manager.load_game_from_file()
            if loaded_game:
                game_var.update(loaded_game)
                print("Game state loaded successfully!")
                print(f"\nWelcome back {name}!!")
                print(f"Total matches played: {game_var['total_matches_played']}")
                print(f"Lifetime runs: {game_var['lifetime_runs']}")
                game_var['balls'] = game_var['over'] * balls_per_over

        elif choice == "profile":
            print("Loading profile...")
            time.sleep(2)
            game_manager.handle_profile_display_and_save(game_var)

        elif choice == "leaderboard":
            print("Attempting to open leaderboard...")
            time.sleep(2)
            leaderboard_manager = LeaderboardManager(db_handler)
            leaderboard_manager.show_menu()

        elif choice == "switch":
            print("Attempting to switch...")
            time.sleep(2)
            new_name = player_login(db_handler)
            if not new_name:
                print("Login failed. Staying with current player.")
                continue
            
            name = new_name
            
            game_var.update({
                "lifetime_runs": 0,
                "lifetime_wickets": 0,
                "total_matches_played": 0,
                "total_wins": 0,
                "total_losses": 0,
                "total_draws": 0,
                "average_runs_per_match": 0,
                "lifetime_balls_faced": 0,   
                "lifetime_balls_bowled": 0,
                "lifetime_runs_conceded": 0,
                "centuries": 0,
                "half_centuries": 0,
            })

            manager = GameDataManager(folder_path_for_json, folder_path_for_excel, name)

            if manager.file_exists():
                print("A pre-existing save with this name was found.")
                while True:
                    try:
                        autosave_load_choice = input("Would you like to load the save file? (yes/no): ").strip().lower()
                        if autosave_load_choice == "yes":
                            print("Loading save game state...")
                            time.sleep(3)
                            loaded_game = manager.load_game_from_file()
                            if loaded_game:
                                game_var.update(loaded_game)
                                print(f"\nWelcome back {name}!!")
                                print(f"Total matches played: {game_var['total_matches_played']}")
                                print(f"Lifetime runs: {game_var['lifetime_runs']}")
                            break
                        elif autosave_load_choice == "no":
                            commentary_enabled = ask_commentary_setting()
                            difficulty = ask_difficulty_setting()
                            game_var["commentary_enabled"] = commentary_enabled
                            game_var["difficulty"] = difficulty
                            profile_data = db_handler.load_profile(name)
                            if profile_data:
                                print("Profile stats loaded from database.")
                                game_var.update(profile_data)
                            break
                        else:
                            print("Enter a valid choice!")
                    except KeyboardInterrupt:
                        print("Game was interrupted, try again")
            else:
                commentary_enabled = ask_commentary_setting()
                difficulty = ask_difficulty_setting()
                game_var["commentary_enabled"] = commentary_enabled
                game_var["difficulty"] = difficulty
                profile_data = db_handler.load_profile(name)
                if profile_data:
                    print("Profile stats loaded from database.")
                    game_var.update(profile_data)

            commentator = Commentator(game_var.get("commentary_enabled", True))
            gameplay = GamePlay(name, min_choice, max_choice, score_alignment, game_var.get('difficulty', 'medium'), commentator)
            display = DisplayManager()
            game_manager = GameManager(gameplay, display, db_handler, manager, name)
            gameplay.intro()

        elif choice == "settings":
            print("Attempting to open the settings menu...")
            time.sleep(2)
            game_manager.show_settings_menu(game_var)

        else:
            print("Invalid Input")
def animated_print(*args, **kwargs):
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    text = sep.join(str(a) for a in args)

    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(0.02)
    sys.stdout.write(end)
    sys.stdout.flush()
if __name__ == "__main__":
    import random
    import pwinput
    import os
    import builtins
    import time
    import sys
    import mysql.connector
    from mysql.connector import Error
    import json
    import pandas as pd
    from openpyxl import load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    
    base_dir = os.path.join(os.path.expanduser("~"), "Documents", "Hand_cricket_saves")
    folder_path_for_json = os.path.join(base_dir, "json_saves")
    folder_path_for_excel = os.path.join(base_dir, "excel_saves")

    os.makedirs(folder_path_for_json, exist_ok=True)
    os.makedirs(folder_path_for_excel, exist_ok=True)

    original_print = print
    builtins.print = animated_print
    
    difficulty = ""

    while True:
        try:
            db_password = pwinput.pwinput("Enter the password to the database: ")
            break
        except KeyboardInterrupt:
            print("\nGame was interrupted, Try again")
    DB_CONFIG = {
        "host": "localhost",
        "user": "root",
        "password": db_password,
        "database": "handcricket"
    }

    _DB = None

    db_handler = HandCricketDB(DB_CONFIG)

    db_handler.create_database()

    db_handler.init_db()

    game_var = {
        'player_runs_1stinn': 0,
        'ai_runs_1stinn': 0,
        'player_runs_2ndinn': 0,
        'ai_runs_2ndinn': 0,
        'toss_result': "",
        'match_summary': {},
        'player_profile': {},
        'balls_played_first_inn': 0,
        'balls_played_sec_inn': 0,
        'total_matches_played': 0,
        'total_wins': 0,
        'total_losses': 0,
        'lifetime_wickets': 0,
        'average_runs_per_match': 0,
        'current_match_wickets': 0,
        'lifetime_runs': 0,
        'over': 0,
        'total_draws': 0,
        'balls': 0,
        'balls_played_by_player': 0,
        'difficulty': 'medium',
        'commentary_enabled': True,
        'lifetime_balls_faced': 0,
        'lifetime_balls_bowled': 0,
        'lifetime_runs_conceded': 0,
        'centuries': 0,
        'half_centuries': 0,
        'player_runs_conceded_1stinn': 0, 
        'player_runs_conceded_2ndinn': 0, 
        'player_balls_bowled_1stinn': 0,  
        'player_balls_bowled_2ndinn': 0,
        'match_result': '',
    }

    name = player_login(db_handler)
    if not name:
        print("No valid player name provided. Exiting game.")
        exit()

    min_choice = 0
    max_choice = 10
    balls_per_over = 6
    score_alignment = 80

    manager = GameDataManager(folder_path_for_json, folder_path_for_excel, name)
    
    if manager.file_exists():
        print("A pre-existing save with this name was found.")
        while True:
            try:
                autosave_load_choice = input("Would you like to load the save file? (yes/no): ").strip().lower()
                if autosave_load_choice == "yes":
                    print("Loading save game state...")
                    time.sleep(3)
                    loaded_game = manager.load_game_from_file()
                    if loaded_game:
                        game_var.update(loaded_game)
                        print(f"\nWelcome back {name}!!")
                        print(f"Total matches played: {game_var['total_matches_played']}")
                        print(f"Lifetime runs: {game_var['lifetime_runs']}")
                        break
                elif autosave_load_choice == "no":
                    commentary_enabled = ask_commentary_setting()
                    difficulty = ask_difficulty_setting()
                    game_var["commentary_enabled"] = commentary_enabled
                    game_var["difficulty"] = difficulty
                    profile_data = db_handler.load_profile(name)
                    if profile_data:
                        print("Profile stats loaded from database.")
                        game_var.update(profile_data)
                    break
                else:
                    print("Enter a valid choice!")
            except KeyboardInterrupt:
                print("Game was interrupted, try again")
    else:
        commentary_enabled = ask_commentary_setting()
        difficulty = ask_difficulty_setting()
        game_var["commentary_enabled"] = commentary_enabled
        game_var["difficulty"] = difficulty
        profile_data = db_handler.load_profile(name)
        if profile_data:
            print("Profile stats loaded from database.")
            game_var.update(profile_data)
    
    commentator = Commentator(game_var.get("commentary_enabled", True))
    gameplay = GamePlay(name, min_choice, max_choice, score_alignment, game_var.get('difficulty', 'medium'), commentator)
    display = DisplayManager()
    game_manager = GameManager(gameplay, display, db_handler, manager, name)
    gameplay.intro()
    time.sleep(1)
    main(game_manager)