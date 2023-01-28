import React from "react";

const CreateGame = (props) => {

    return (
        <div>
            <form>
            <p>Create Game</p>
            <label htmlFor="nick_name">NickName:</label>
            <input type="text" id="nick_name" name="nick_name" />
            <br/>
            <input type="submit" value="Submit" />
            </form>
        </div>
    )
}


export default CreateGame;