import random

from monty_hall import simulate_monty_hall


def test_switching_wins_more_often_than_staying():
    switch_rate = simulate_monty_hall(5000, switch_doors=True, rng=random.Random(7))
    stay_rate = simulate_monty_hall(5000, switch_doors=False, rng=random.Random(11))

    assert switch_rate > 0.6
    assert switch_rate > stay_rate


def test_switching_wins_about_two_thirds_of_the_time():
    switch_rate = simulate_monty_hall(5000, switch_doors=True, rng=random.Random(13))

    assert 0.6 < switch_rate < 0.75
