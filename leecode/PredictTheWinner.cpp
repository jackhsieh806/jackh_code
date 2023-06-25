class Solution {
public:
    bool PredictTheWinner(vector<int>& nums) {
        int n = nums.size();
        vector<vector<int>> dp(n,vector<int>(n,0));

        for(int i = 0; i < n; i++) {
            dp[i][i] = nums[i];
        }

        
        for (int j = 1; j < n; j++) {
            for (int k = 0; k+j < n; k ++) {
                dp[k][k+j] = max(nums[k]-dp[k+1][k+j],nums[k+j] - dp[k][k+j-1]);
            }           
        }
        printf("dp[0][n-1] = %d\r\n", dp[0][n-1]);
        if (dp[0][n-1] >= 0)
            return true;

        return false;
    }
};
