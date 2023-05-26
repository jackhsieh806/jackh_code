class Solution {
public:
    int candy(vector<int>& ratings) {
        int n = ratings.size();
        vector<int> candy(n,1);
        int count = 0;

        for (int i = 0; i < n-1; i++) {
            if (ratings[i+1] > ratings[i]) {
                if (candy[i+1] <= candy[i]) {
                    count+=  (candy[i] - candy[i+1] + 1);
                    candy[i+1] = candy[i]+1;
                }                         
            }
        }


        for (int i = n-1; i > 0; i--) {
            if (ratings[i-1] > ratings[i]) {
                if (candy[i-1] <= candy[i]) {
                    count+=  (candy[i] - candy[i-1] + 1);
                    candy[i-1] = candy[i]+1;
                }
            }
        }        

        return count+n;
    }
};
