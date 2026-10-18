#include <vector>
using namespace std;

vector<int> twoSum(vector<int>& nums, int target) {
  for (int i = 0; i < (int)nums.size(); i++) {
    for (int j = i + 1; j < (int)nums.size(); j++) {
      if (nums[i] + nums[j] == target) return {i, j};
    }
  }
  return {};
}
