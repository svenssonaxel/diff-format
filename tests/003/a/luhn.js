function check(str) {
    let sum = 0;
    const digits = String(str).replace(/[^0-9]/g, '');
    if(digits=='') {
        return false;
    }
    for(const [index, value] of digits.split('').reverse().map(x => Number.parseInt(x)).entries()) {
        sum += index % 2 ? [0, 2, 4, 6, 8, 1, 3, 5, 7, 9][value] : value;
    }
    return (sum % 10) == 0;
}

module.exports.check = check;
