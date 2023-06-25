class Solution {
public:
    int magicalString(int n) {
        vector<unsigned char> magic;
        int index = 2;
        int cur = 3;
        int num = 1; //start num
        int res = 0;
        magic.push_back(1);
        magic.push_back(2);
        magic.push_back(2);
        if (n == 0)
            return 0;

        if (n <= 3)
            return 1;

        while (magic.size() <= n) {
            if (magic[index] == 1) {
                magic.push_back(num);
            } else {
                magic.push_back(num);
                magic.push_back(num);
            }
            index++;
            if (num == 1)
                num = 2;
            else
                num = 1;
        }
        for (int i = 0; i < n; i++) {
            if (magic[i] == 1)
                res++;
        }
        return res;
    }
};
