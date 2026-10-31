#include <iostream>

#include <list.hpp>

int main()
{
  Designar::SLList<int> numbers;
  numbers.append(1);
  numbers.append(2);
  numbers.append(3);

  std::cout << "DeSiGNAR OK: " << numbers.size() << " elements\n";
  return 0;
}
