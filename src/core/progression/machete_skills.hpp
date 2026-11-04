#pragma once

#include <string>

#include <core/progression/skill_tree.hpp>

// Ids in the tree; the order of the table in machete_skills.cpp follows them.
namespace MacheteSkill
{
constexpr int MACHETE = 0;
constexpr int EDGE_1 = 1;
constexpr int EDGE_2 = 2;
constexpr int EDGE_3 = 3;
constexpr int GREASE = 4;
constexpr int FIRE = 5;
constexpr int ICE = 6;
constexpr int TECHNIQUE = 7;
constexpr int THROW = 8;
constexpr int RAGE = 9;
constexpr int COUNT = 10;
constexpr int NONE = -1;
}

constexpr float EDGE_DAMAGE = 0.15f; // Per Filo level.

struct MacheteSkillInfo
{
  const char * key; // Saves name skills by this, as with items.
  const char * name;
  const char * description;
  int parent;
  int cost; // In day-0 lochas: the bachaquero adds his inflation and markup.
};

const MacheteSkillInfo & machete_skill(int id);
int find_machete_skill(const std::string & key); // MacheteSkill::NONE if unknown.

// Machete ├─ Filo → Filo II → Filo III
//         ├─ Grasa → Fuego / Hielo
//         └─ Técnica → Lanzar machete / Modo Arrechera
SkillTree make_machete_tree();
