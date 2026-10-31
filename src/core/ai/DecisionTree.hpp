#pragma once

#include <queue.hpp>
#include <core/distance.hpp>
#include <core/attack.hpp>

class DecisionTree {
    private:
    Designar::DynQueue<Attack> near_attacks;
    Designar::DynQueue<Attack> medium_attacks;
    Designar::DynQueue<Attack> far_attacks;

    public:
    
    DecisionTree(const Designar::DynQueue<Attack>& na, const Designar::DynQueue<Attack>& ma, const Designar::DynQueue<Attack>& fa);
    const Attack evaluate(const DistanceRange distance_category);
};