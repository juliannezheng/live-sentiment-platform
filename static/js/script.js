document.addEventListener('DOMContentLoaded', function() {
    var socket = io();

    socket.on('user_update', function(data) {
        if (data.full_name && data.table_selection) {
            var fullName = data.full_name;
            var tableSelection = data.table_selection;
            var action = data.action;

            if (action === 'join') {
                addUser(fullName, tableSelection);
            } else if (action === 'leave') {
                removeUser(fullName);
            }
        }
    });

    socket.on('color_update', function(data) {
        if (data.full_name && data.color) {
            var fullName = data.full_name;
            var color = data.color;

            updateUserColor(fullName, color);
        }
    });

    window.addEventListener('beforeunload', function() {
        var fullName = getUserFullName(); // Replace this with your own logic to get the user's full name
        if (fullName) {
            deleteUser(fullName);
        }
    });

    var userForm = document.getElementById('userForm');
    userForm.addEventListener('submit', function(event) {
        event.preventDefault();
        var fullNameInput = document.getElementById('full_name');
        var fullName = fullNameInput.value.trim();
        if (fullName) {
            setUserFullName(fullName);
        }
        userForm.submit();
    });

    function addUser(fullName, tableSelection) {
        var tableColumn = getTableColumnBySelection(tableSelection);
        if (tableColumn) {
            var newUserBox = createUserBox(fullName);
            tableColumn.appendChild(newUserBox);
            // Create a remove button for each user
            var removeButton = document.createElement('button');
            removeButton.textContent = 'Remove';
            removeButton.onclick = function() {
                removeUser(fullName);
            };
            newUserBox.appendChild(removeButton);
        }
    }

    function removeUser(fullName) {
        var userBox = document.querySelector('.user-box.' + fullName);
        if (userBox) {
            userBox.parentNode.removeChild(userBox);
        }
    }

    function updateUserColor(fullName, color) {
        var userBox = document.querySelector('.user-box.' + fullName);
        if (userBox) {
            userBox.classList.remove('red', 'yellow', 'green');
            userBox.classList.add(color);
        }
    }

});
