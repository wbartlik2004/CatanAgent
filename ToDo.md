game state all set, need agents done in next 2 days

0 main runner to get whole games simmed, maybe with uniform selection
1 Greedy Agent/baseline
2 MCTS
3 Coevolution

Alright 0 is done

We've debated a good bit about whether to train agents on 2p or 4p,
and I think that we should develop agents on 2-player catan until they're at their final state.

There's less variance at 2p and some of the positive strategies agents develop at 4p might
only be such because their turn is right after a worse agent, strategy works particularly well against
the agents its playing, etc

Therefore there is way more noise/not real trends at 4p than there is at 2p

Also the issue that 4p is much less 0-sum than 2p:
    Player 3 could, in theory, make moves that contribute more to the success of Player 2 than
    they do to Player 3.
    Then, when Player 2 wins the game, who's to say whether it won because its moves were actually good
    or because Player 3 didn't properly punish Player 2 for those moves

Tldr I think that when we train our agents (maybe this isnt true for coevolution) they should be trained on 2p games because we will need to sim wayyyyy more 4p games to drown out noise

On the runner being done:
It's very simple, in reality we've kinda of built the rest of the engine around the runner.

You can comment out/not use the "if name == main" block, it was just for testing to make sure
we were running porperly. My "verbose" func also sucks, feel free to change.

We need to run some tests using the runner to make sure the engine is really following rules:
- distribution of dice rolls
- settlement/road/city/robber visualization would be so lit
    - could tell whether all placement rules are being followed
- stealing
- trading

This might be too time-intensive for where we are right now, and maybe this could
sort of be implemented in parallel with agents just for testing while they sim ifk.