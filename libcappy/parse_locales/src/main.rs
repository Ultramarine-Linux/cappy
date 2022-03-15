use std::process::Command;
use regex::Regex;

fn main() {
    let output = Command::new("sh")
        .arg("-c")
        .arg("locale -av")
        .output()
        .expect("Fail to execute program");
    
    let res = String::from_utf8_lossy(&output.stdout);

    let re = Regex::new(r"(?s)le: (\S+).+?le \| (.+?)\n").unwrap();
    for cap in re.captures_iter(&res) {
        println!("{}|{}", &cap[1], &cap[2])
    }
}
