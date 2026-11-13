#include <core/progression/machete_skills.hpp>

namespace
{
// A parent always comes before its children, so the tree can be built in one pass.
constexpr MacheteSkillInfo SKILLS[MacheteSkill::COUNT] = {
  {"machete", "Machete", "El de siempre.", MacheteSkill::NONE, 0},
  {"edge_1", "Filo", "Una piedra y paciencia. Más daño con el machete.", MacheteSkill::MACHETE, 60},
  {"edge_2", "Filo II", "Afilado hasta cortar papel. Más daño.", MacheteSkill::EDGE_1, 120},
  {"edge_3", "Filo III", "No queda óxido. Mucho más daño.", MacheteSkill::EDGE_2, 200},
  {"grease", "Grasa", "Aprendes a engrasar la hoja. Abre las grasas.", MacheteSkill::MACHETE, 40},
  {"fire", "Fuego", "El bachaquero te vende grasa de fuego: quema con el tiempo.", MacheteSkill::GREASE, 80},
  {"ice", "Hielo", "El bachaquero te vende grasa de hielo: frena al enemigo.", MacheteSkill::GREASE, 80},
  {"technique", "Técnica", "Le agarras el ritmo al machete. Abre las técnicas.", MacheteSkill::MACHETE, 60},
  {"throw", "Lanzar machete", "G: va y vuelve. Mientras vuela no puedes atacar.", MacheteSkill::TECHNIQUE, 120},
  {"rage", "Modo Arrechera", "V con la barra llena: pegas más fuerte unos 12 s, pero recibes más daño.", MacheteSkill::TECHNIQUE, 160},
};
}

const MacheteSkillInfo & machete_skill(int id)
{
  return SKILLS[id];
}

int find_machete_skill(const std::string & key)
{
  // Ten keys, read only while loading a game: a straight scan is enough.
  for (int id = 0; id < MacheteSkill::COUNT; ++id)
    if (key == SKILLS[id].key)
      return id;
  return MacheteSkill::NONE;
}

SkillTree make_machete_tree()
{
  SkillTree tree(MacheteSkill::MACHETE);
  for (int id = 1; id < MacheteSkill::COUNT; ++id)
    tree.add(SKILLS[id].parent, id, SKILLS[id].cost);
  return tree;
}
