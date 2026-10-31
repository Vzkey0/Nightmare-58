#include "DecisionTree.hpp"

DecisionTree::DecisionTree(const Designar::DynQueue<Attack>& na, const Designar::DynQueue<Attack>& ma, const Designar::DynQueue<Attack>& fa) : near_attacks(na), medium_attacks(ma), far_attacks(fa) {}

const Attack DecisionTree::evaluate(const DistanceRange distance_category) {
    Attack active_attack;

    if (distance_category == DistanceRange::Near) {
        active_attack = near_attacks.get();
        near_attacks.put(active_attack);
        return active_attack;
    }
    else if (distance_category == DistanceRange::Medium) {
        active_attack = medium_attacks.get();
        medium_attacks.put(active_attack);
        return active_attack;
    }

    active_attack = far_attacks.get();
    far_attacks.put(active_attack);
    return active_attack;
}