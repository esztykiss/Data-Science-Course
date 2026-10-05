import random

DOORS = (0, 1, 2)


def simulate_monty_hall(num_trials: int = 100_000, switch_doors: bool = True, rng: random.Random | None = None) -> float:
    """Simulate the Monty Hall problem and return the win rate."""
    if rng is None:
        rng = random.Random()

    wins = 0

    for _ in range(num_trials):
        prize_door = rng.randrange(len(DOORS))
        first_choice = rng.randrange(len(DOORS))

        goat_doors = [door for door in DOORS if door not in (prize_door, first_choice)]
        opened_door = goat_doors[0]

        if switch_doors:
            final_choice = next(door for door in DOORS if door not in (first_choice, opened_door))
        else:
            final_choice = first_choice

        if final_choice == prize_door:
            wins += 1

    return wins / num_trials


def explain_monty_hall() -> str:
    return (
        "The winning strategy is to switch. "
        "At the start, you have a 1/3 chance to pick the prize. "
        "The host always opens a goat door, so the remaining unopened door keeps the other 2/3 chance."
    )


def main() -> None:
    switch_rate = simulate_monty_hall(100_000, switch_doors=True)
    stay_rate = simulate_monty_hall(100_000, switch_doors=False)

    print(f"Stay with your first choice: {stay_rate:.2%}")
    print(f"Switch doors: {switch_rate:.2%}")
    print(explain_monty_hall())


if __name__ == "__main__":
    main()
