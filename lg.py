import random
import time
import sys



NUM_INNOCENTS = 8
NUM_LIARS = 12
LIAR_DECK_SIZE = NUM_INNOCENTS + NUM_LIARS  # 20
REVOLVER_DECK_SIZE = 6  # 1 Lethal, 5 Blanks
STARTING_HAND_SIZE = 5
AI_CALL_LIAR_CHANCE = 0.3
AI_PLAY_CARD_CHANCE = 0.7
AI_MAX_CARDS_TO_PLAY = 3

# DATA STRUCTURES

class LiarDeck:
    def __init__(self):
        self.cards = []
        self.build_deck()
        self.shuffle()

    def build_deck(self):
        self.cards = ["I"] * NUM_INNOCENTS + ["L"] * NUM_LIARS

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self, n=1):
        """
        Draw 'n' cards from the top of the deck.
        Return them as a list.
        If the deck has fewer than n cards, returns what's left.
        """
        drawn = self.cards[:n]
        self.cards = self.cards[n:]
        return drawn

    def reset_and_shuffle(self):
        self.build_deck()
        self.shuffle()

class RevolverDeck:
    def __init__(self):
        self.cards = ["X"] + ["_"] * 5  # 1 lethal, 5 blanks
        self.shuffle()

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self):
        if not self.cards:
            return None
        top = self.cards[0]
        self.cards = self.cards[1:]
        return top

class Player:
    """
     - name
     - hand (list of Liar cards: "I" or "L")
     - revolver deck
     - eliminated status
    """
    def __init__(self, name, is_human=False):
        self.name = name
        self.hand = []
        self.revolver = RevolverDeck()
        self.eliminated = False
        self.is_human = is_human

    def has_cards(self):
        return len(self.hand) > 0

    def remove_cards_from_hand(self, indexes):
        removed_cards = []
        for idx in sorted(indexes, reverse=True):
            removed_cards.append(self.hand[idx])
            del self.hand[idx]
        return removed_cards

    def draw_revolver(self):
        card = self.revolver.draw()
        return (card == "X")


class LiarsBarGame:
    def __init__(self, num_players=3, human_index=0):
        if not (2 <= num_players <= 4):
            print("Warning: Game is recommended for 2 to 4 players. Proceeding anyway.")

        self.num_players = num_players
        self.human_index = human_index

        self.players = []
        for i in range(num_players):
            is_human = (i == human_index)
            self.players.append(Player(name=f"Player {i+1}", is_human=is_human))

        self.liar_deck = LiarDeck()

        self.current_start_player = random.randint(0, num_players-1)

        self.current_player_index = self.current_start_player

        self.last_played_cards = []
        self.last_played_player_index = None

    def active_players(self):
        return [p for p in self.players if not p.eliminated]

    def next_player_index(self, start_index=None):
        if start_index is None:
            start_index = self.current_player_index
        n = len(self.players)
        idx = (start_index + 1) % n
        while self.players[idx].eliminated:
            idx = (idx + 1) % n
        return idx

    def all_but_one_eliminated(self):
        count_not_elim = sum(not p.eliminated for p in self.players)
        return count_not_elim <= 1

    def get_winner(self):
        alive_players = [p for p in self.players if not p.eliminated]
        if len(alive_players) == 1:
            return alive_players[0]
        return None

    def deal_cards_for_round(self):
        self.liar_deck.reset_and_shuffle()
        for p in self.players:
            if not p.eliminated:
                p.hand = self.liar_deck.draw(STARTING_HAND_SIZE)

    def run_game(self):
        """
        Main loop: run rounds until only one player remains (or none).
        """
        print("=== Welcome to Liar's Bar Game (Single-Player Demo) ===")
        round_number = 1

        while True:
            if self.all_but_one_eliminated():
                break

            print(f"\n--- ROUND {round_number} START ---")
            self.run_round()

            round_number += 1

            if self.all_but_one_eliminated():
                break

        winner = self.get_winner()
        if winner:
            print(f"\n*** {winner.name} wins! ***")
        else:
            print("\nAll players have been eliminated simultaneously. No winner.")

    def run_round(self):
        self.deal_cards_for_round()
        self.current_player_index = self.current_start_player

        self.last_played_cards = []
        self.last_played_player_index = None

        round_over = False

        while not round_over:
            round_over = self.check_force_liar_call()
            if round_over:
                break

            if self.all_but_one_eliminated():
                break

            player = self.players[self.current_player_index]
            if player.eliminated:
                self.current_player_index = self.next_player_index()
                continue
            if not player.has_cards():
                self.current_player_index = self.next_player_index()
                continue

            round_over = self.take_turn(player)

            if not round_over:
                self.current_player_index = self.next_player_index()

    def check_force_liar_call(self):
        players_with_cards = [i for i, p in enumerate(self.players) if (not p.eliminated and p.has_cards())]
        if len(players_with_cards) == 1 and self.last_played_player_index is not None:
            lone_player_index = players_with_cards[0]
            if lone_player_index != self.last_played_player_index:
                print(f"{self.players[lone_player_index].name} is forced to call LIAR on {self.players[self.last_played_player_index].name}!")
                return self.handle_liar_call(
                    accuser_index=lone_player_index,
                    accused_index=self.last_played_player_index
                )
        return False

    def take_turn(self, player):
        if player.is_human:
            return self.human_turn(player)
        else:
            return self.ai_turn(player)

    def human_turn(self, player):
        print(f"\nYour turn, {player.name}. You have {len(player.hand)} card(s).")
        print("Your hand (hidden to others) =>", player.hand)
        time.sleep(0.5)

        valid_actions = []
        if self.last_played_player_index is not None and self.last_played_player_index != self.current_player_index:
            valid_actions.append("LIAR")

        print("\nActions:")
        if valid_actions:
            print("  - LIAR (call Liar on the previous player's face-down play)")
        print("  - PLAY n (where n = 1..3) [only if you have enough cards]")

        choice = None
        while True:
            raw_input_val = input("Choose your action (e.g. 'PLAY 2' or 'LIAR'): ").strip().upper()
            if raw_input_val.startswith("PLAY"):
                parts = raw_input_val.split()
                if len(parts) == 2 and parts[0] == "PLAY" and parts[1].isdigit():
                    num_to_play = int(parts[1])
                    if 1 <= num_to_play <= 3 and num_to_play <= len(player.hand):
                        choice = ("PLAY", num_to_play)
                        break
                    else:
                        print("Invalid number of cards to play.")
            elif raw_input_val == "LIAR":
                if "LIAR" in valid_actions:
                    choice = ("LIAR", 0)
                    break
                else:
                    print("You cannot call LIAR at this moment.")
            else:
                print("Invalid choice. Try again.")

        if choice[0] == "LIAR":
            print(f"\n{player.name} calls 'LIAR' on {self.players[self.last_played_player_index].name}!")
            return self.handle_liar_call(
                accuser_index=self.current_player_index,
                accused_index=self.last_played_player_index
            )
        else:
            num_to_play = choice[1]
            print("\nYour hand:", list(enumerate(player.hand)))
            chosen_indexes = []
            while len(chosen_indexes) < num_to_play:
                try:
                    card_index = int(input(f"Choose card index to play ({len(chosen_indexes)+1}/{num_to_play}): "))
                    if 0 <= card_index < len(player.hand) and card_index not in chosen_indexes:
                        chosen_indexes.append(card_index)
                    else:
                        print("Invalid index or already chosen, try again.")
                except ValueError:
                    print("Please enter a valid number.")

            played_cards = player.remove_cards_from_hand(chosen_indexes)
            print(f"You played {num_to_play} card(s) face down.\n")
            self.last_played_cards = played_cards
            self.last_played_player_index = self.current_player_index
            time.sleep(1)
            return False

    def ai_turn(self, player):
        print(f"\n{player.name}'s turn (AI). They have {len(player.hand)} card(s).")
        time.sleep(1)

        can_liar = (self.last_played_player_index is not None and 
                    self.last_played_player_index != self.current_player_index)

        if can_liar:
            if random.random() < AI_CALL_LIAR_CHANCE:
                print(f"{player.name} calls 'LIAR' on {self.players[self.last_played_player_index].name}!")
                return self.handle_liar_call(
                    accuser_index=self.current_player_index,
                    accused_index=self.last_played_player_index
                )

        num_to_play = random.randint(1, min(AI_MAX_CARDS_TO_PLAY, len(player.hand)))
        played_cards_idx = random.sample(range(len(player.hand)), num_to_play)
        played_cards = player.remove_cards_from_hand(played_cards_idx)
        print(f"{player.name} plays {num_to_play} card(s) face down.\n")
        self.last_played_cards = played_cards
        self.last_played_player_index = self.current_player_index
        time.sleep(1)
        return False

    def handle_liar_call(self, accuser_index, accused_index):
        if not self.last_played_cards:
            print("No cards to reveal! This is effectively a false accusation.\n")
            liar_found = False
        else:
            print(f"{self.players[accused_index].name}'s last played cards:", self.last_played_cards)
            liar_found = any(card == "L" for card in self.last_played_cards)

        if liar_found:
            print(f"At least one Liar card found! {self.players[accused_index].name} must draw from their Revolver!")
            lethal = self.players[accused_index].draw_revolver()
            if lethal:
                print(f"** BANG! {self.players[accused_index].name} is eliminated! **")
                self.players[accused_index].eliminated = True
            else:
                print(f"{self.players[accused_index].name} got a blank. They survive this time.")
            next_round_player = accused_index
        else:
            print(f"No Liar cards found! {self.players[accuser_index].name} made a false accusation and must draw!")
            lethal = self.players[accuser_index].draw_revolver()
            if lethal:
                print(f"** BANG! {self.players[accuser_index].name} is eliminated! **")
                self.players[accuser_index].eliminated = True
            else:
                print(f"{self.players[accuser_index].name} got a blank. They survive.")
            next_round_player = accuser_index

        if self.players[next_round_player].eliminated:
            next_round_player = self.next_player_index(next_round_player)

        self.current_start_player = next_round_player
        return True


if __name__ == "__main__":
    game = LiarsBarGame(num_players=4, human_index=0)
    game.run_game()

    print("\nThank you for playing the Liar's Bar Game demo!")