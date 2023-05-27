class Solution {
public:
    string stoneGameIII(vector<int>& stoneValue) {
        int alice = 0,bob = 0;
        int sum = 0;
        int n = stoneValue.size();

        vector<int> dp(n+3,0);

        for (int i = n-1; i >= 0; i--) {
            sum+=stoneValue[i];
            dp[i] = max(max(sum-dp[i+1],sum-dp[i+2]),sum-dp[i+3]);
        }
        printf("dp[0] = %d\r\n", dp[0]);
        alice = dp[0];
        bob = sum-dp[0];
        printf("alice max = %d, Bob max = %d\r\n", alice, bob);

        if (alice > bob)
            return "Alice";
        else if (alice < bob)
            return "Bob";
        else
            return "Tie";
    }


    string stoneGameIII_2(vector<int>& stoneValue) {
        int alice = 0,bob = 0;
        stoneDfs(alice,bob,0,stoneValue);
        printf("alice max = %d, Bob max = %d\r\n", alice, bob);
        if (alice > bob)
            return "Alice";
        else if (alice < bob)
            return "Bob";
        else
            return "Tie";
    }

    void stoneDfs(int &p1,int &p2,int idx, vector<int>& stoneValue) {
            int sz = stoneValue.size();
            int maxp1 = 0;
            int maxp2 = 0;
            int temp = 0;

            p1 = 0;
            p2 = 0;

            if (idx > sz - 1)
                return; 
            /*       
            if (idx + 2 >= sz - 1) {            
                for (int i = idx; i < sz; i++) 
                    p1 += stoneValue[i];                
                if (p1 >= 0)
                    return;
                if (idx > sz -1) {
                    return;
                }
            }*/
            stoneDfs(p1,p2,idx+1,stoneValue);
            maxp1 = p2+stoneValue[idx];
            maxp2 = p1;
            //printf("temp1 = %d\r\n", maxp1);
            if (idx+2 > sz) {
                p1 = maxp1;
                p2 = maxp2;                
                return;
            }
            stoneDfs(p1,p2,idx+2,stoneValue);
            temp = p2+stoneValue[idx]+stoneValue[idx+1];
            //printf("temp2 = %d\r\n", temp);            
            if (maxp1 < temp) {
                maxp1 = temp;
                maxp2 = p1;
            }
            if (idx+3 > sz) {
                p1 = maxp1;
                p2 = maxp2;
                return;
            }
            stoneDfs(p1,p2,idx+3,stoneValue);
            temp = p2+stoneValue[idx]+stoneValue[idx+1]+stoneValue[idx+2];
            //printf("temp3 = %d\r\n", temp);     
            if (maxp1 < temp) {
                maxp1 = temp;
                maxp2 = p1;
            }
            p1 = maxp1;
            p2 = maxp2;

            return;
        }    
};
