/**
 * Definition for a binary tree node.
 * struct TreeNode {
 *     int val;
 *     TreeNode *left;
 *     TreeNode *right;
 *     TreeNode() : val(0), left(nullptr), right(nullptr) {}
 *     TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
 *     TreeNode(int x, TreeNode *left, TreeNode *right) : val(x), left(left), right(right) {}
 * };
 */
class Solution {
public:
    TreeNode* constructMaximumBinaryTree(vector<int>& nums) {
        int n = nums.size()-1;
        return findMax(nums,0,n);
    }

    TreeNode* findMax(vector<int>& nums, int a, int b) {
        int maxv = nums[a];
        int maxv_i = a;
        if (a == b) { return new TreeNode(nums[a]);}
        for (int i = a+1; i <= b ;i++) {
            if (maxv < nums[i]) {
                maxv = nums[i];
                maxv_i = i;
            }
        }
        TreeNode* node = new TreeNode(maxv);
        if (maxv_i != a) {
            node->left = findMax(nums,a,maxv_i-1);
        }

        if (maxv_i != b) {
            node->right = findMax(nums,maxv_i+1,b);
        }

        return node;
    }
};
