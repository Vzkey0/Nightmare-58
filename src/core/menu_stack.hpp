#pragma once

#include <stack.hpp>

enum class MenuScreen { Chapel, Stats, Inventory };

// Going back returns to the row the player left, on any depth of menu.
class MenuStack
{
public:
  static constexpr int MAX_DEPTH = 4;

  bool is_open() const { return !screens.is_empty(); }
  MenuScreen screen() const { return screens.top().screen; }
  int cursor() const { return screens.top().cursor; }

  void open(MenuScreen screen) { screens.push(Entry{screen, 0}); }
  void back() { screens.pop(); }
  void close() { screens.clear(); }

  void move_cursor(int step, int rows)
  {
    if (rows > 0)
      screens.top().cursor = (screens.top().cursor + step + rows) % rows;
  }

  // For a list that got shorter while it was open.
  void keep_cursor_within(int rows)
  {
    if (screens.top().cursor >= rows)
      screens.top().cursor = rows > 0 ? rows - 1 : 0;
  }

private:
  struct Entry
  {
    MenuScreen screen;
    int cursor;
  };

  // J-014: menus nest in the order they close, and never deeper than this.
  Designar::FixedStack<Entry, MAX_DEPTH> screens;
};
