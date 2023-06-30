class Solution {
public:

    double new21Game(int n, int k, int maxPts) {
        vector<double> dp(maxPts+n+1,0);
        double res = 1;
        double cacheAmount = 0;
        for (int i = n+maxPts; i >= 0; i--) {
            if (i >= k) {
                if (i > n )
                    dp[i] = 0;
                else
                    dp[i] = 1;
            } else {
                if (cacheAmount == 0) {
                    for (int j = i+1; j <= i + maxPts; j++) {
                        cacheAmount += dp[j];
                        dp[i] += dp[j]/maxPts;
                    }
                } else {
                    cacheAmount += dp[i+1];
                    cacheAmount -= dp[i + maxPts +1];
                    dp[i] = cacheAmount/maxPts;
                }
            }
        }
        return dp[0];

    }
 
};
