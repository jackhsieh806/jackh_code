#include <stdio.h>
#include <vector>
#include <string>

using namespace std;
string findMaxSarlayPath(vector<int> &a, vector<int> &b);
int main()
{
    printf("Hello World");
    vector<int> a = {115,30,1,2,7000,180};
    vector<int> b = {3,3,1010,20,70,180};
    findMaxSarlayPath(a,b);

    return 0;
}

string findMaxSarlayPath(vector<int> &a, vector<int> &b) {
    int n = a.size();
    vector<vector<pair<int,string>>> dp(n, vector<pair<int, string>>(4,make_pair(0, "")));
    //dp[x][0] = from x to n-1 day,max x day work in a city salay
    //dp[x][1] = from x to n-1 day,max x day work in b city salay
    //dp[x][2] = from x to n-1 day,max x day from a city trip for b salay
    //dp[x][3] = from x to n-1 day,max x day from b city trip for a salay
    
    dp[n-1][0] = make_pair(a[n-1],"a");
    dp[n-1][1] = make_pair(b[n-1],"b"); //last day
    
    for (int i = n-2; i >= 0; i--) {
        //in a city
        dp[i][0] = make_pair(dp[i+1][0].first+a[i], "a"+dp[i+1][0].second);
        if (i+2 < n) {
            if (dp[i][0].first < dp[i+2][1].first+a[i]) //trip to b 
                dp[i][0] = make_pair(dp[i+2][1].first+a[i], "a."+dp[i+2][1].second);
        }
        dp[i][1] = make_pair(dp[i+1][1].first+b[i], "b"+dp[i+1][1].second);
         if (i+2 < n) {
            if (dp[i][1].first < dp[i+2][0].first+b[i]) //trip to a
                dp[i][1] = make_pair(dp[i+2][0].first+b[i], "b."+dp[i+2][0].second);
         }
    }
    if (dp[0][0].first > dp[0][1].first) {
        printf("res = %s, max salary = %d\r\n", dp[0][0].second.c_str(), dp[0][0].first);
        return dp[0][0].second;
    }
    else    
        printf("res = %s, max salary = %d\r\n", dp[0][1].second.c_str(), dp[0][1].first);
    
    return dp[0][1].second;
}
