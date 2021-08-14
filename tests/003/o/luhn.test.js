const assert = require('assert');
const luhn = require('./luhn.js');

const testCases = [
    {str: '12344', result: true},
    {str: '0012344', result: true},
    {str: '123 - ABC 44', result: true},
    {str: '01.23-44Q', result: true},
    {str: '12345', result: false},
    {str: '0012345', result: false},
    {str: '123 - ABC 45', result: false},
    {str: '01.23-45Q', result: false},
];

for(const {str, result} of testCases){
    assert(luhn.check(str)==result, `Failed test:${JSON.stringify({str, result})}`)
}
