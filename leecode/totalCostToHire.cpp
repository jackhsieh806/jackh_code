class Solution {
public:
    long long totalCost(vector<int>& costs, int k, int candidates) {
        int i = 0;
        int j = costs.size() - 1;
        priority_queue<int, vector<int>, greater<int>> pq1;
        priority_queue<int, vector<int>, greater<int>> pq2;

        long long ans = 0;
        while(k--){
            while(pq1.size() < candidates && i <= j){
                pq1.push(costs[i++]);
            }
            while(pq2.size() < candidates && i <= j){
                pq2.push(costs[j--]);
            }

            int t1 = pq1.size() > 0 ? pq1.top() : INT_MAX;
            int t2 = pq2.size() > 0 ? pq2.top() : INT_MAX;

            if(t1 <= t2){
                ans += t1;
                pq1.pop();
            }
            else{
                ans += t2;
                pq2.pop();
            }
        }
        return ans;
    }
    long long totalCost2(vector<int>& costs, int k, int candidates) {
        priority_queue<int,vector<int>,greater<int>> lq;
        priority_queue<int,vector<int>,greater<int>> rq;
        int n = costs.size();
        int l = candidates, r = n-1 - candidates;
        long long res = 0;

        for (int i = 0; i < candidates; i++) {
            lq.push(costs[i]);
            if (i < (n-1-i))
                rq.push(costs[n-1-i]);
        }
        while (k > 0 && lq.size() > 0 && rq.size() > 0) {            
            if (lq.top() < rq.top()) {
                printf("choose lq %d\r\n",lq.top());
                res += lq.top(); lq.pop();
                
                if (l <= r) {
                    lq.push(costs[l]);          
                    l++;
                }
            } else {
                printf("choose rq %d\r\n",rq.top());
                res += rq.top(); rq.pop();
                if (l <= r) {
                    rq.push(costs[r]);                
                    r--;
                }
            }
            k--;
        }
        if (k > 0) {
            if (lq.size() > 0) {
                while(k>0) {
                    res+=lq.top();
                    lq.pop();
                    k--;
                }
            }
            if (rq.size() > 0) {
                while(k>0) {
                    res+=rq.top();
                    rq.pop();
                    k--;
                }
            }            
        }

        return res;

    }
};
