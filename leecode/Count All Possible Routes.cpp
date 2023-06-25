class Solution {
private:
    int dp[201][100];    
public:

    int countRoutes(vector<int>& locations, int start, int finish, int fuel) {
        long long r = 0;
        int n = locations.size();
        int M = 1e9+7;
        //vector<vector<int>> dp(200,vector<int>(n,0));
        memset(dp,0,sizeof(int)*100*201);
        for (int i = 0; i <= fuel; i++)
            dp[i][finish] = 1;


        for (int f = 1; f <= fuel; f++) {
            for(int i = 0; i < n; i++) {
                for(int j = 0; j < n; j++) {
                    if (i != j) {
                        if (abs(locations[j]-locations[i]) <= f) {
                            dp[f][i] = (dp[f][i] + dp[f-abs(locations[j]-locations[i])][j])%M;
                        }
                    }                
                }
            }
        }
        return dp[fuel][start];
        //return r;
    }
    int countRoutes_iter(vector<int>& locations, int start, int finish, int fuel) {
        long long r = 0;
        if (fuel < 0)
            return 0;

        if (start == finish)
            r = 1;

        if (fuel == 0)
            return r;
        

        for (int i = 0; i < locations.size(); i++) {
            if (i != start) {
                r += countRoutes(locations,i,finish,fuel - abs(locations[i]-locations[start]));
            }
        }

        return r%100000007;
        //return r;
    }
};
