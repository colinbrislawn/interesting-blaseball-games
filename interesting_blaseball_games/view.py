import time
import sys
import os
from rich.console import Console
from rich.table import Table
from .game_data import GameData, REASON2FUNCTION
from .util import (
    sanitize_dale,
    get_league_division_team_data
)


NAMESTYLE_CHOICES = ['long', 'short', 'emoji']


class View(object):
    """
    Base class for view classes, so that they all have
    the same options variables available.
    """
    def __init__(self, options):
        self.nresults = options.n_results
        self.game_data = GameData(options)
        self.column_headers, self.nice_column_headers = self.assemble_column_headers(options)
        self.name_style = options.name_style

        # For table description
        self.options = options

        # If an output file is specified, check if it exists and if the path to it exists
        if options.output == '':
            self.output_file = None
        else:
            self.output_file = options.output
            if os.path.exists(self.output_file):
                print("WARNING: Overwriting an existing file %s"%(self.output_file))
                print("Waiting 5 seconds before proceeding")
                time.sleep(5)
                # Clear out the file
                with open(self.output_file, 'w') as f:
                    f.write("")
            else:
                output_file_path = os.path.abspath(os.path.dirname(self.output_file))
                if not os.path.exists(output_file_path):
                    raise Exception("Error: directory for output file (%s) does not exist!"%(output_file_path))

    def make_table(self):
        """Virtual method to make table(s)"""
        raise NotImplementedError("View class is a base class, do not call it directly")

    def table_description(self, reason):
        """
        Create table descriptions for each table, customizing
        based on filters the user provides
        """
        options = self.options
        if reason == 'blowout':
            desc = "Blowout games (games with high scores and high run differentials) "
        elif reason == 'shutout':
            desc = "Shutout games (games where the loser had zero runs) "
        elif reason == 'shame':
            desc = "Shame games (games where the loser was shamed) "
        elif reason == 'underdog':
            desc = "Underdog games (games where the underdog won with large run differential) "
        elif reason == 'maxedout':
            desc = "Maxed out games (high-scoring one-run games) "
        elif reason == 'defensive':
            desc = "Defensive games (low-scoring one-run games) "
        else:
            raise Exception("Error: reason not recognized. Valid reasons: %s"%(", ".join(list(REASON2FUNCTION.keys()))))

        if 'all' in options.season:
            desc += "for all time "
        else:
            if len(options.season)==1:
                desc += "for season %s "%("".join(options.season))
            else:
                desc += "for seasons %s "%(", ".join(options.season))

        if options.postseason :
            desc += "(postseason only) "

        _, _, ALLTEAMS = get_league_division_team_data()
        if len(options.team)==1:
            desc += "for team %s"%("".join(options.team))
        elif len(set(ALLTEAMS) - set(options.team)) == 0:
            desc += "for all teams"
        else:
            desc += "for teams %s"%(", ".join(options.team))

        desc += " (note: all days and seasons displayed are 1-indexed)"
        return desc

    def assemble_column_headers(self, options):
        """
        Create a list of column names to show in the final table.
        These should be in their correct final order.

        If organizing by winner/loser:
        Season | Game | Winning Pitcher | Winning Team | Winning Runs | Losing Runs | Losing Team | Losing Pitcher

        If organizing by home/away:
        Season | Game | Home Pitcher | Home Team | Home Runs | Away Runs | Away Team | Away Pitcher

        The column names are the dataframe column names,
        the nice column names are for printing.

        (pitcher columns are optional)
        """
        column_names = ['season', 'day', 'isPostseason']
        nice_column_names = ["Sea", "Day", "Post"]

        # Next columns will be winner/loser or home/away,
        # depending on the win_loss vs home_away options.
        if options.win_loss:

            # Winning pitcher
            if options.winning_pitcher:
                column_names.append('winningPitcherName')
                nice_column_names.append("WP")

            # Winning team name
            if options.name_style=='long':
                column_names.append('winningTeamName')
            elif options.name_style=='short':
                column_names.append('winningTeamNickname')
            elif options.name_style=='emoji':
                column_names.append('winningTeamEmoji')
            nice_column_names.append("Winner")

            # W odds (not printed)
            column_names.append("winningOdds")
            nice_column_names.append("W Odds")

            # Score
            column_names.append('winningLosingScore')
            nice_column_names.append("Score")

            # L odds (not printed)
            column_names.append("losingOdds")
            nice_column_names.append("L Odds")

            # Losing team name
            if options.name_style=='long':
                column_names.append('losingTeamName')
            elif options.name_style=='short':
                column_names.append('losingTeamNickname')
            elif options.name_style=='emoji':
                column_names.append('losingTeamEmoji')
            nice_column_names.append("Loser")

            # Losing pitcher
            if options.losing_pitcher:
                column_names.append('losingPitcherName')
                nice_column_names.append("LP")

        elif options.home_away:

            # Home pitcher
            if options.home_pitcher:
                column_names.append('homePitcherName')
                nice_column_names.append("Home P")

            # Home team name
            if options.name_style=='long':
                column_names.append('homeTeamName')
            elif options.name_style=='short':
                column_names.append('homeTeamNickname')
            elif options.name_style=='emoji':
                column_names.append('homeTeamEmoji')
            nice_column_names.append("Home")

            # H odds (not printed)
            column_names.append("homeOdds")
            nice_column_names.append("A Odds")

            # Score
            column_names.append('homeAwayScore')
            nice_column_names.append("Score")

            # A odds (not printed)
            column_names.append("awayOdds")
            nice_column_names.append("A Odds")

            # Away team name
            if options.name_style=='long':
                column_names.append('awayTeamName')
            elif options.name_style=='short':
                column_names.append('awayTeamNickname')
            elif options.name_style=='emoji':
                column_names.append('awayTeamEmoji')
            nice_column_names.append("Away")

            # Away pitcher
            if options.away_pitcher:
                column_names.append('awayPitcherName')
                nice_column_names.append("Away P")

        return (column_names, nice_column_names)


class RichView(View):
    """
    Create a table and render it using rich
    """
    def make_table(self):
        """
        Get a list of DataFrames and descriptions, 
        and render them as tables with rich.
        """
        # Get dataframes and descriptions
        tables = self.game_data.parse()
        for table in tables:
            reason, df = table
            desc = self.table_description(reason)
            self._render_table(desc, df, reason)

    def _render_table(self, description, df, reason):
        """
        Render a table using rich
        """
        # Cut data to table data only
        cut = df[self.column_headers][:min(len(df), self.nresults)].copy()

        # Bump season and game numbers by one (zero-indexed in dataframe)
        # (Pandas is soooo intuitive)
        plusone = lambda x : x + 1
        new_season_column = cut['season'].apply(plusone)
        new_game_column = cut['day'].apply(plusone)
        cut = cut.assign(**{'season': new_season_column, 'day': new_game_column})

        # Create name and odds labels
        if self.options.win_loss:
            pre = ['winning','losing']
        else:
            pre = ['home','away']

        if self.options.name_style=='short':
            namelabels = [j + 'TeamNickname' for j in pre]
        elif self.options.name_style=='long':
            namelabels = [j + 'TeamName' for j in pre]
        elif self.options.name_style=='emoji':
            namelabels = [j + 'TeamEmoji' for j in pre]

        oddslabels = [j + 'Odds' for j in pre]

        # Replace Team with Team (X%)
        if reason=='underdog':
            # Eventually we may want to do this with ALL reasons
            for namelabel, oddslabel in zip(namelabels, oddslabels):
                addodds = lambda row: "%s (%d%%)"%(row[namelabel], round(100*row[oddslabel]))
                try:
                    cut[namelabel] = cut[[namelabel, oddslabel]].apply(addodds, axis=1)
                except KeyError:
                    print(cut.columns)
                    print(cut)
                    sys.exit(1)

        # Remove the odds columns
        cut.drop(oddslabels, axis=1, inplace=True)

        # Remove the odds headers
        self.column_headers = [j for j in self.column_headers if 'Odds' not in j]
        self.nice_column_headers = [j for j in self.nice_column_headers if 'Odds' not in j]

        # Format the isPostseason column for printing (empty space if not, else Y)
        postseason_lambda = lambda c: ' ' if c is False else 'Y'
        new_postseason_column = cut['isPostseason'].apply(postseason_lambda)
        cut = cut.assign(**{'isPostseason': new_postseason_column.values})

        # Format any column ending in "Emoji" as emoji (hope this works!)
        # (there must be a more efficient way to do this, but I really, really hate pandas now.)
        for column_header in self.column_headers:
            emoji_lambda = lambda x: chr(int(x, 16))
            if column_header[-5:]=='Emoji':
                new_column = cut[column_header].apply(emoji_lambda)
                cut = cut.assign(**{column_header: new_column})

        # Make everything in the dataframe a string
        cut = cut.applymap(str)

        console = Console()

        console.print("\n\n")

        table = Table(show_header=True, header_style="bold")

        for column_header, nice_column_header in zip(self.column_headers, self.nice_column_headers):
            if column_header=="losingScore" or column_header=="awayScore":
                # Justify losing/away scores to the right (opposite winning/home scores)
                table.add_column(nice_column_header, justify="right")
            elif self.name_style=="emoji" and column_header[-5:]=="Emoji":
                # Center emoji team name columns
                table.add_column(nice_column_header, justify="center")
            else:
                table.add_column(nice_column_header)

        for i, row in cut.iterrows():
            table.add_row(*row.values)

        console.print(table)
        console.print("\n")
        print(description)
        console.print("\n\n")


class MarkdownView(View):
    """
    Create a table and render it as a Markdown table
    """
    # TODO: integrate some of the shared rich/markdown view functionality
    def make_table(self):
        """
        Get list of DataFrames and descriptions,
        and render each one as Markdown table
        """
        tables = self.game_data.parse()
        for table in tables:
            reason, df = table
            desc = self.table_description(reason)
            desc += " (asterisk indicates a postseason game)"
            self._render_table(desc, df, reason)

    def _render_table(self, description, df, reason):
        """
        Render a table as a Markdown table
        """
        # Cut data to table data only
        cut = df[self.column_headers][:min(len(df), self.nresults)].copy()

        # Bump season and game numbers by one (zero-indexed in dataframe)
        # (Pandas is soooo intuitive)
        plusone = lambda x : x + 1
        new_season_column = cut['season'].apply(plusone)
        new_game_column = cut['day'].apply(plusone)
        cut = cut.assign(**{'season': new_season_column, 'day': new_game_column})

        # Create name and odds labels
        if self.options.win_loss:
            pre = ['winning','losing']
        else:
            pre = ['home','away']

        if self.options.name_style=='short':
            namelabels = [j + 'TeamNickname' for j in pre]
        elif self.options.name_style=='long':
            namelabels = [j + 'TeamName' for j in pre]
        elif self.options.name_style=='emoji':
            namelabels = [j + 'TeamEmoji' for j in pre]

        oddslabels = [j + 'Odds' for j in pre]

        # Replace Team with Team (X%)
        if reason=='underdog':
            # Eventually we may want to do this with ALL reasons
            for namelabel, oddslabel in zip(namelabels, oddslabels):
                addodds = lambda row: "%s (%d%%)"%(row[namelabel], round(100*row[oddslabel]))
                try:
                    cut[namelabel] = cut[[namelabel, oddslabel]].apply(addodds, axis=1)
                except KeyError:
                    print(cut.columns)
                    print(cut)
                    sys.exit(1)


        # Remove the odds columns
        cut.drop(oddslabels, axis=1, inplace=True)

        # Remove the odds headers
        self.column_headers = [j for j in self.column_headers if 'Odds' not in j]
        self.nice_column_headers = [j for j in self.nice_column_headers if 'Odds' not in j]

        # Format the isPostseason column for printing (empty space if not, else Y)
        postseason_lambda = lambda c: '' if c is False else '*'
        new_postseason_column = cut['isPostseason'].apply(postseason_lambda)
        cut = cut.assign(**{'isPostseason': new_postseason_column.values})

        # Format any column ending in "Emoji" as emoji (hope this works!)
        # (there must be a more efficient way to do this, but I really, really hate pandas now.)
        for column_header in self.column_headers:
            emoji_lambda = lambda x: chr(int(x, 16))
            if column_header[-5:]=='Emoji':
                new_column = cut[column_header].apply(emoji_lambda)
                cut = cut.assign(**{column_header: new_column})

        # Make everything in the dataframe a string
        cut = cut.applymap(str)

        # This string is the final table in Markdown format
        table = ""

        # Start header line
        table_header = "| "
        # Start separator line (controls alignment)
        table_sep = "| "
        for column_header, nice_column_header in zip(self.column_headers, self.nice_column_headers):
            if column_header == 'isPostseason':
                continue
            table_header += "%s | "%(nice_column_header)
            if column_header=="losingScore" or column_header=="awayScore":
                # Justify losing/away scores to the right (opposite winning/home scores)
                table_sep += "------: | "
            elif self.name_style=="emoji" and column_header[-5:]=="Emoji":
                # Center emoji team name columns
                table_sep += ":------: | "
            else:
                table_sep += "------ |"

        table += table_header
        table += "\n"
        table += table_sep
        table += "\n"

        for i, row in cut.iterrows():
            table_row = "| "
            for k, val in zip(row.keys(), row.values):
                if k == 'isPostseason':
                    continue
                elif k == 'day':
                    table_row += "%s%s | "%(str(val), row['isPostseason'])
                else:
                    table_row += "%s | "%(str(val))
            table += table_row
            table += "\n"

        # TODO
        # Something something, DRY
        # Something something, more pythonic
        if self.output_file is None:
            print("\n\n")
            print(description)
            print("\n")
            print(table)
        else:
            with open(self.output_file, 'a') as f:
                f.write("\n\n")
                f.write(description)
                f.write("\n")
                f.write(table)

